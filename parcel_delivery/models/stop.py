from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parcel_delivery.models.parcel import Parcel

class Stop:
    """Represents a stop on the courier's route"""

    def __init__(self, location: int, stop_type: str, parcel: "Parcel"):
        self.location: int = location
        self.stop_type: str = stop_type
        self.parcel: "Parcel" = parcel