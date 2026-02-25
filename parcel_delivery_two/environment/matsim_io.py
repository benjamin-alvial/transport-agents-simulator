import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge


def load_network_from_matsim(filepath: str) -> Network:
    """Parse a MATSim network XML file and return a Network.

    Reads ``<node>`` elements for id/x/y and ``<link>`` elements for
    id/from/to/length/freespeed. All other attributes (capacity,
    permlanes, …) are ignored.

    Args:
        filepath: Path to a MATSim network XML file (network_v1.dtd).

    Returns:
        A Network populated with Node and Edge objects.

    Raises:
        FileNotFoundError: If filepath does not exist.
        xml.etree.ElementTree.ParseError: If the file is not valid XML.
    """
    root = ET.parse(filepath).getroot()

    network = Network()

    for elem in root.find("nodes"):
        network.add_node(Node(
            node_id=int(elem.get("id")),
            x=float(elem.get("x")),
            y=float(elem.get("y")),
        ))

    for elem in root.find("links"):
        network.add_edge(Edge(
            edge_id=int(elem.get("id")),
            from_node=int(elem.get("from")),
            to_node=int(elem.get("to")),
            distance=float(elem.get("length")),
            free_flow_speed=float(elem.get("freespeed")),
        ))

    return network


_BIN_SIZE = 900  # 15-minute bins in seconds


def load_historic_travel_times(filepath: str, network: Network) -> None:
    """Compute historic average travel times from a MATSim events file and
    attach them to the edges of the network.

    Travel time for each link traversal is measured as the difference between
    the exit-link event time and the enter-link event time. Traversals are
    grouped into 15-minute bins by their entry time and averaged across all
    vehicles. The result is stored in ``edge.travel_times`` as a mapping of
    bin-start (seconds) to average travel time (seconds).

    Edges that receive no traffic are left with an empty ``travel_times`` dict.
    Events referencing links absent from the network are silently ignored.

    Args:
        filepath: Path to a MATSim events XML file (e.g. ``5.events.xml``).
        network: The Network whose edges will be annotated in-place.

    Raises:
        FileNotFoundError: If filepath does not exist.
        xml.etree.ElementTree.ParseError: If the file is not valid XML.
    """
    root = ET.parse(filepath).getroot()

    # vehicle_id -> (entry_time, edge_id)
    in_flight: Dict[str, Tuple[float, int]] = {}

    # (edge_id, bin_start) -> list of observed travel times
    samples: Dict[Tuple[int, int], List[float]] = defaultdict(list)

    for event in root:
        event_type = event.get("type")
        t = float(event.get("time"))

        if event_type == "entered link":
            vehicle = event.get("vehicle")
            link = int(event.get("link"))
            in_flight[vehicle] = (t, link)

        elif event_type == "left link":
            vehicle = event.get("vehicle")
            if vehicle in in_flight:
                entry_time, link = in_flight.pop(vehicle)
                travel_time = t - entry_time
                bin_start = int(entry_time // _BIN_SIZE) * _BIN_SIZE
                samples[(link, bin_start)].append(travel_time)

    for (edge_id, bin_start), times in samples.items():
        if edge_id in network.edges:
            network.edges[edge_id].travel_times[bin_start] = sum(times) / len(times)
