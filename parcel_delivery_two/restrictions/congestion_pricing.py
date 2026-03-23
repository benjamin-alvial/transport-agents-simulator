from typing import Optional, List


class CongestionPricing:
    """Congestion pricing toll on an edge that adds cost to certain vehicles.

    When ``vehicle_type`` is ``None`` the pricing applies to all vehicle types.
    When ``time_window`` is specified, the pricing only applies during that
    time interval [start, end] in seconds. If ``None``, the pricing is always
    active.

    The cost represents the monetary fee (in dollars) for traversing the edge.
    During routing, this is converted to a time-equivalent using the courier's
    Value of Travel Time (VTT) so it can be combined with travel time costs.

    Args:
        edge_id: ID of the edge to apply pricing to.
        cost: Monetary cost in dollars for traversing the edge.
        vehicle_type: Vehicle type string to apply pricing to, or ``None`` for all.
        time_window: Optional list [start_time, end_time] in seconds defining
            when the pricing is active. If None, always active.
    """

    def __init__(
        self,
        edge_id: int,
        cost: float,
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
        self.cost = cost
        self.vehicle_type = vehicle_type
        self.time_window = time_window

    def applies(self, vehicle_type: str, time: Optional[float] = None) -> bool:
        """Return ``True`` if this pricing applies to *vehicle_type* at *time*.

        Args:
            vehicle_type: The vehicle type string to test.
            time: Optional time in seconds to check against time_window.
                If None and time_window is set, returns False.

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

    def get_cost(self, vehicle_type: str, time: Optional[float] = None) -> float:
        """Return the congestion cost if applicable, otherwise 0.

        Args:
            vehicle_type: The vehicle type string to test.
            time: Optional time in seconds to check against time_window.

        Returns:
            The cost in dollars if the pricing applies, otherwise 0.0.
        """
        if self.applies(vehicle_type, time):
            return self.cost
        return 0.0
