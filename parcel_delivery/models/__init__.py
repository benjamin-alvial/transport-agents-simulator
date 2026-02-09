"""
Data models for the parcel delivery simulation.

Contains core data structures used throughout the core:
    - Parcel: Represents a package to be delivered
    - Stop: Represents a location on a courier's route
    - Bid: Represents a bid done by a courier within an auction
    - Occupancy: Represents the occupancy of a vehicle in an edge
"""

from .parcel import Parcel
from .stop import Stop
from .bid import Bid
from .occupancy import Occupancy

__all__ = [
    "Parcel",
    "Stop",
    "Bid",
    "Occupancy",
]
