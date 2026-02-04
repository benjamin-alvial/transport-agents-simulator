"""
Parcel Delivery Simulation

A discrete-event core framework for modeling parcel delivery systems.
"""

# Import from submodules to make them available at package level
from .core import Agent, Entity, Event, Kernel, Message
from .entities import Auction, Bus, Courier, Customer, Platform
from .environment import Edge, Network, Node
from .models import Bid, Parcel, Stop

# Package metadata
__version__ = "0.1.0"

# Define public API
__all__ = [
    "Agent",
    "Entity",
    "Event",
    "Kernel",
    "Message",
    "Auction",
    "Bus",
    "Courier",
    "Customer",
    "Platform",
    "Edge",
    "Network",
    "Node",
    "Bid",
    "Parcel",
    "Stop",
]