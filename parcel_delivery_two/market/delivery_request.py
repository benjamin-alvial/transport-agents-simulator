from typing import Optional


class DeliveryRequest:
    """A single parcel delivery request issued by a customer.

    Attributes:
        name: Unique identifier for the request.
        weight: Weight of the parcel (used for capacity checks).
        origin: Node ID where the parcel must be picked up.
        destination: Node ID where the parcel must be delivered.
        start_time: Simulation time when delivery journey started (set by vehicle).
        completion_time: Simulation time when parcel was delivered.
    """

    def __init__(self, name: str, weight: float, origin: int, destination: int):
        self.name = name
        self.weight = weight
        self.origin = origin
        self.destination = destination
        self.start_time: Optional[float] = None
        self.completion_time: Optional[float] = None

    def get_delivery_time(self) -> Optional[float]:
        """Calculate the time taken to deliver this request.

        Returns:
            Delivery time in seconds, or None if not yet completed.
        """
        if self.start_time is not None and self.completion_time is not None:
            return self.completion_time - self.start_time
        return None
