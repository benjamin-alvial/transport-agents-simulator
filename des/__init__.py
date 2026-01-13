"""
DES - Discrete Event Simulation Framework
"""

from des.kernel import SimulationKernel, Event
from des.agents import Agent
from des.message import Message

__version__ = '0.1.0'
__all__ = ['SimulationKernel', 'Event', 'Agent', 'Message']