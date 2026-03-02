import gzip
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple, TextIO, BinaryIO, Union

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge


def _open_file(filepath: str) -> Union[TextIO, BinaryIO]:
    """Open file, auto-detecting gzip compression."""
    if filepath.endswith('.gz'):
        return gzip.open(filepath, 'rt', encoding='utf-8')
    return open(filepath, 'r', encoding='utf-8')


def load_network_from_matsim(filepath: str) -> Network:
    """Parse a MATSim network XML file and return a Network (streaming).

    Reads ``<node>`` elements for id/x/y and ``<link>`` elements for
    id/from/to/length/freespeed. All other attributes (capacity,
    permlanes, …) are ignored.

    MATSim may use string IDs (e.g., "node_1", "link_10") or integer IDs.
    This function maps each original MATSim ID to an internal integer ID:
    - If the MATSim ID is a numeric string (e.g., "1", "10"), it is converted
      to an integer and used as the internal ID (backward compatible).
    - If the MATSim ID is non-numeric (e.g., "node_1"), a sequential internal
      ID is assigned (0, 1, 2, ...).

    The mapping is preserved in the Network for later reference via
    ``node_id_to_matsim`` / ``matsim_to_node_id`` and
    ``edge_id_to_matsim`` / ``matsim_to_edge_id``.

    Args:
        filepath: Path to a MATSim network XML file (network_v1.dtd).
            Supports .gz compressed files.

    Returns:
        A Network populated with Node and Edge objects.

    Raises:
        FileNotFoundError: If filepath does not exist.
        xml.etree.ElementTree.ParseError: If the file is not valid XML.
    """
    network = Network()

    context = ET.iterparse(_open_file(filepath), events=('start', 'end'))
    context = iter(context)
    event, root = next(context)

    for event, elem in context:
        if event == 'end':
            tag = elem.tag
            if tag == 'node':
                matsim_id = elem.get("id")
                assert matsim_id is not None, "Node must have an id attribute"
                try:
                    internal_id = int(matsim_id)
                except ValueError:
                    internal_id = len(network.nodes)

                x_attr = elem.get("x")
                y_attr = elem.get("y")
                assert x_attr is not None and y_attr is not None, "Node must have x and y attributes"

                network.add_node(Node(
                    node_id=internal_id,
                    x=float(x_attr),
                    y=float(y_attr),
                ))
                network.node_id_to_matsim[internal_id] = matsim_id
                network.matsim_to_node_id[matsim_id] = internal_id

                elem.clear()

            elif tag == 'link':
                matsim_id = elem.get("id")
                from_matsim = elem.get("from")
                to_matsim = elem.get("to")
                assert matsim_id is not None and from_matsim is not None and to_matsim is not None, \
                    "Link must have id, from, and to attributes"

                from_internal = network.matsim_to_node_id.get(from_matsim)
                if from_internal is None:
                    try:
                        from_internal = int(from_matsim)
                    except ValueError:
                        from_internal = len(network.nodes)
                    network.matsim_to_node_id[from_matsim] = from_internal

                to_internal = network.matsim_to_node_id.get(to_matsim)
                if to_internal is None:
                    try:
                        to_internal = int(to_matsim)
                    except ValueError:
                        to_internal = len(network.nodes)
                    network.matsim_to_node_id[to_matsim] = to_internal

                try:
                    internal_id = int(matsim_id)
                except ValueError:
                    internal_id = len(network.edges)

                length_attr = elem.get("length")
                freespeed_attr = elem.get("freespeed")
                assert length_attr is not None and freespeed_attr is not None, \
                    "Link must have length and freespeed attributes"

                network.add_edge(Edge(
                    edge_id=internal_id,
                    from_node=from_internal,
                    to_node=to_internal,
                    distance=float(length_attr),
                    free_flow_speed=float(freespeed_attr),
                ))
                network.edge_id_to_matsim[internal_id] = matsim_id
                network.matsim_to_edge_id[matsim_id] = internal_id

                elem.clear()

    return network


_BIN_SIZE = 900  # 15-minute bins in seconds


def load_historic_travel_times(filepath: str, network: Network) -> None:
    """Compute historic average travel times from a MATSim events file and
    attach them to the edges of the network (streaming).

    Travel time for each link traversal is measured as the difference between
    the exit-link event time and the enter-link event time. Traversals are
    grouped into 15-minute bins by their entry time and averaged across all
    vehicles. The result is stored in ``edge.travel_times`` as a mapping of
    bin-start (seconds) to average travel time (seconds).

    Edges that receive no traffic are left with an empty ``travel_times`` dict.
    Events referencing links absent from the network are silently ignored.

    MATSim events use string link IDs. If the network was loaded via
    ``load_network_from_matsim``, the function uses the ``matsim_to_edge_id``
    mapping. Otherwise, it attempts to parse the link ID as an integer.

    Args:
        filepath: Path to a MATSim events XML file (e.g. ``5.events.xml``).
            Supports .gz compressed files.
        network: The Network whose edges will be annotated in-place.

    Raises:
        FileNotFoundError: If filepath does not exist.
        xml.etree.ElementTree.ParseError: If the file is not valid XML.
    """
    has_mapping = bool(network.matsim_to_edge_id)

    # vehicle_id -> (entry_time, link_id)
    in_flight: Dict[str, Tuple[float, str]] = {}

    # (link_id, bin_start) -> (sum_times, count)
    accumulators: Dict[Tuple[str, int], List[float]] = defaultdict(lambda: [0.0, 0])

    context = ET.iterparse(_open_file(filepath), events=('end',))

    for event, elem in context:
        if elem.tag == 'event':
            event_type = elem.get("type")
            time_attr = elem.get("time")
            assert time_attr is not None, "Event must have a time attribute"
            t = float(time_attr)

            if event_type == "entered link":
                vehicle = elem.get("vehicle")
                link = elem.get("link")
                assert vehicle is not None and link is not None, \
                    "entered link event must have vehicle and link attributes"
                in_flight[vehicle] = (t, link)

            elif event_type == "left link":
                vehicle = elem.get("vehicle")
                if vehicle in in_flight:
                    entry_time, link = in_flight.pop(vehicle)
                    travel_time = t - entry_time
                    bin_start = int(entry_time // _BIN_SIZE) * _BIN_SIZE
                    acc = accumulators[(link, bin_start)]
                    acc[0] += travel_time
                    acc[1] += 1

            elem.clear()

    for (link_id, bin_start), (total, count) in accumulators.items():
        internal_edge_id = None

        if has_mapping and link_id in network.matsim_to_edge_id:
            internal_edge_id = network.matsim_to_edge_id[link_id]
        else:
            try:
                internal_edge_id = int(link_id)
            except ValueError:
                pass

        if internal_edge_id is not None and internal_edge_id in network.edges:
            network.edges[internal_edge_id].travel_times[bin_start] = total / count
