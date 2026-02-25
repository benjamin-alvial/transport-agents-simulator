class DeliveryRequest:
    """A single parcel delivery request issued by a customer.

    Attributes:
        name: Unique identifier for the request.
        weight: Weight of the parcel (used for capacity checks).
        destination: Node ID of the delivery destination.
    """

    def __init__(self, name: str, weight: float, destination: int):
        self.name = name
        self.weight = weight
        self.destination = destination
