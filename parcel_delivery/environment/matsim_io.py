import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List

from parcel_delivery.environment.network import Network
from parcel_delivery.environment.edge import Edge
from parcel_delivery.environment.node import Node

def load_network_from_matsim(filepath: str):
    tree = ET.parse(filepath)
    root = tree.getroot()

    network = Network()

    for node_el in root.find("nodes"):
        node_id = int(node_el.get("id"))
        x = float(node_el.get("x"))
        y = float(node_el.get("y"))
        network.nodes[node_id] = Node(node_id=node_id, x=x, y=y)

    for link_el in root.find("links"):
        from_node = int(link_el.get("from"))
        to_node = int(link_el.get("to"))
        distance = float(link_el.get("length"))
        capacity = float(link_el.get("capacity"))

        edge = Edge(
            from_node=from_node,
            to_node=to_node,
            distance=distance,
            capacity=capacity,
        )

        if from_node not in network.edges:
            network.edges[from_node] = {}
        network.edges[from_node][to_node] = edge
        network.edges_by_link_id[int(link_el.get("id"))] = edge

    return network

def _iter_events(filepath: str):
    """Memory-efficient event iteration using iterparse."""
    for _, elem in ET.iterparse(filepath, events=("end",)):
        if elem.tag == "event":
            yield elem
            elem.clear()

def load_historic_travel_times(events_filepath: str, network: "Network") -> None:
    """
    Parse a MATSim events file and populate historic_travel_times
    on each edge in the network.
    """
    # entry_times[vehicle][link_id] = entry_time
    entry_times: Dict[str, Dict[int, float]] = defaultdict(dict)

    # accumulators: slot_data[link_id][slot] = list of travel times
    slot_data: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))

    for event in _iter_events(events_filepath):
        etype = event.get("type")
        time = float(event.get("time", 0))

        if etype == "entered link":
            vehicle = event.get("vehicle")
            link_id = int(event.get("link"))
            entry_times[vehicle][link_id] = time

        elif etype == "left link":
            vehicle = event.get("vehicle")
            link_id = int(event.get("link"))

            if vehicle in entry_times and link_id in entry_times[vehicle]:
                entry_time = entry_times[vehicle].pop(link_id)
                travel_time = time - entry_time
                slot = int(entry_time // 900) % 96
                slot_data[link_id][slot].append(travel_time)

    # Write averages into edges
    for link_id, slots in slot_data.items():
        edge = network.edges_by_link_id.get(link_id)
        if edge:
            for slot, times in slots.items():
                edge.historic_travel_times[slot] = sum(times) / len(times)
