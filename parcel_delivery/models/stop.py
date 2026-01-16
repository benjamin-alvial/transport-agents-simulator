from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parcel_delivery.models.parcel import Parcel

class Stop:
    """Represents a stop on the courier's route"""

    def __init__(self, location: int, type: str, parcel: "Parcel"):
        self.location: int = location
        self.type: str = type
        self.parcel: "Parcel" = parcel