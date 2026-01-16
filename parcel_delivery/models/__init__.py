"""
Data models for the parcel delivery simulation.

Contains core data structures used throughout the simulation:
    - Parcel: Represents a package to be delivered
    - Stop: Represents a location on a courier's route
"""

from .parcel import Parcel
from .stop import Stop

__all__ = [
    "Parcel",
    "Stop",
]
