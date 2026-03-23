from typing import Optional, List


class ProhibitEdge:
    """Restriction that forbids one edge from being used by certain vehicles.

    When ``vehicle_type`` is ``None`` the restriction applies to all vehicle
    types. Otherwise only vehicles whose ``vehicle_type`` matches are affected.

    When ``time_window`` is specified, the restriction only applies during that
    time interval [start, end] in seconds. If ``None``, the restriction is always
    active.

    Args:
        edge_id: ID of the edge to prohibit.
        vehicle_type: Vehicle type string to restrict, or ``None`` for all.
        time_window: Optional list [start_time, end_time] in seconds defining
            when the restriction is active. If None, always active.
    """

    def __init__(
        self,
        edge_id: int,
        vehicle_type: Optional[str] = None,
        time_window: Optional[List[float]] = None,
    ):
        if time_window is not None:
            if len(time_window) != 2:
                raise ValueError("time_window must be a list of exactly 2 elements [start, end]")
            start, end = time_window
            if end < start:
                raise ValueError(f"time_window end ({end}) must be >= start ({start})")
        self.edge_id = edge_id
        self.vehicle_type = vehicle_type
        self.time_window = time_window

    def blocks(self, vehicle_type: str, time: Optional[float] = None) -> bool:
        """Return ``True`` if this restriction blocks *vehicle_type* at *time*.

        Args:
            vehicle_type: The vehicle type string to test.
            time: Optional time in seconds to check against time_window.
                If None and time_window is set, returns False (restriction not active).

        Returns:
            ``True`` when vehicle type matches AND (time_window is None OR
            time falls within the time_window interval).
        """
        # Check vehicle type match
        type_matches = self.vehicle_type is None or self.vehicle_type == vehicle_type
        if not type_matches:
            return False

        # Check time window if specified
        if self.time_window is not None:
            if time is None:
                return False
            start, end = self.time_window
            if not (start <= time <= end):
                return False

        return True
