class DeliveryRequest:
    """A single parcel delivery request issued by a customer.

    Attributes:
        name: Unique identifier for the request.
        weight: Weight of the parcel (used for capacity checks).
        origin: Node ID where the parcel must be picked up.
        destination: Node ID where the parcel must be delivered.
    """

    def __init__(self, name: str, weight: float, origin: int, destination: int):
        self.name = name
        self.weight = weight
        self.origin = origin
        self.destination = destination
