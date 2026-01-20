"""
Core simulation infrastructure.

Contains the fundamental building blocks for the simulation:
    - SimulationKernel: Main discrete-event simulation engine
    - Event: An event that can be scheduled in the simulator
    - Message: A message that can be sent between agents
"""

from .kernel import Kernel
from .event import Event
from .message import Message

__all__ = [
    "Kernel",
    "Event",
    "Message",
]