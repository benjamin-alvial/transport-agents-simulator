"""
Agents module for the parcel delivery simulation.

This module contains all agent implementations that participate in the
delivery simulation system.

Available agents:
    - Platform: Manages parcel requests and assigns them to couriers
    - Customer: Requests parcel deliveries
    - Courier: Delivers parcels from origin to destination
    - Auction: Represents an auction for a parcel
"""

from .agent import Agent
from .courier import Courier
from .customer import Customer
from .platform import Platform
from .auction import Auction

__all__ = [
    "Agent",
    "Courier",
    "Customer",
    "Platform",
    "Auction",
]
