"""
Core simulation infrastructure.

Contains the fundamental building blocks for the simulation:
    - SimulationKernel: Main discrete-event simulation engine
    - Event: An event that can be scheduled in the simulator
    - Message: A message that can be sent between agents
    - Network: The road network in which the simulation takes place
"""

from .kernel import Kernel
from .event import Event
from .message import Message
from .network import Network

__all__ = [
    "Kernel",
    "Event",
    "Message",
    "Network"
]