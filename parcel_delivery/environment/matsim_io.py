import xml.etree.ElementTree as ET

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

    return network