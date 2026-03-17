"""Depot class for parcel delivery market."""


class Depot:
    """A depot where couriers start and delivery requests originate.

    Attributes:
        depot_id: Unique identifier for the depot.
        node_id: Node ID in the network where this depot is located.
    """

    def __init__(self, depot_id: str, node_id: int):
        """Initialize a depot.

        Args:
            depot_id: Unique identifier for the depot.
            node_id: Node ID in the network where this depot is located.
        """
        self.depot_id = depot_id
        self.node_id = node_id
