"""
Contains the classes used to represent the environment in which the simulation takes place.

The main structures are:
    - Network: The road network in which the core takes place
    - Node: Represents a node in the road network
    - Edge: Represents an edge in the road network
"""

from .network import Network
from .node import Node
from .edge import Edge

__all__ = [
    "Network",
    "Node",
    "Edge",
]