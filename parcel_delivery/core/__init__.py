"""
Core simulation infrastructure.

Contains the fundamental building blocks for the core:
    - Kernel: Main discrete-event core engine
    - Event: An event that can be scheduled in the simulator
    - Entity: An active "thing" in the simulation
    - Agent: An entity that can communicate with others and make decisions
    - Message: A message that can be sent between agent entities
"""

from .kernel import Kernel
from .event import Event
from .entity import Entity
from .agent import Agent
from .message import Message

__all__ = [
    "Kernel",
    "Event",
    "Entity",
    "Agent",
    "Message",
]