from typing import Optional


class ProhibitEdge:
    """Restriction that forbids one edge from being used by certain vehicles.

    When ``vehicle_type`` is ``None`` the restriction applies to all vehicle
    types. Otherwise only vehicles whose ``vehicle_type`` matches are affected.

    Args:
        edge_id: ID of the edge to prohibit.
        vehicle_type: Vehicle type string to restrict, or ``None`` for all.
    """

    def __init__(self, edge_id: int, vehicle_type: Optional[str] = None):
        self.edge_id = edge_id
        self.vehicle_type = vehicle_type

    def blocks(self, vehicle_type: str) -> bool:
        """Return ``True`` if this restriction blocks *vehicle_type*.

        Args:
            vehicle_type: The vehicle type string to test.

        Returns:
            ``True`` when ``self.vehicle_type`` is ``None`` (all vehicles
            are blocked) or when it matches *vehicle_type* exactly.
        """
        return self.vehicle_type is None or self.vehicle_type == vehicle_type
