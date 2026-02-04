"""
Entities module for the parcel delivery core.

This module contains all entity implementations that participate in the
delivery simulation system.

Available entities:
    - Customer: Requests parcel deliveries
    - Auction: Represents an auction for a parcel
    - Platform: Manages parcel requests, generates auctions, and assigns parcels to couriers
    - Courier: Delivers parcels from origins to destinations
    - Bus: Transports passengers to their destinations
"""

from .customer import Customer
from .auction import Auction
from .platform import Platform
from .courier import Courier
from .bus import Bus

__all__ = [
    "Customer",
    "Auction",
    "Platform",
    "Courier",
    "Bus",
]
