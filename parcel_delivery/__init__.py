"""
Parcel Delivery Simulation

A discrete-event simulation framework for modeling parcel delivery systems
with platforms, customers, and couriers.
"""

# Import from submodules to make them available at package level
from .agents import Agent, Courier, Customer, Platform
from .models import Parcel, Stop, Node
from .simulation import Event, Kernel, Message, Network

# Package metadata
__version__ = "0.1.0"

# Define public API
__all__ = [
    "Agent",
    "Courier",
    "Customer",
    "Platform",
    "Parcel",
    "Stop",
    "Event",
    "Kernel",
    "Message",
    "Node",
    "Network"
]