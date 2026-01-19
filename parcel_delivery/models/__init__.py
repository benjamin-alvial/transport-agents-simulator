"""
Data models for the parcel delivery simulation.

Contains core data structures used throughout the simulation:
    - Parcel: Represents a package to be delivered
    - Stop: Represents a location on a courier's route
    - Bid: Represents a bid done by a courier within an auction
"""

from .parcel import Parcel
from .stop import Stop
from .bid import Bid

__all__ = [
    "Parcel",
    "Stop",
    "Bid",
]
