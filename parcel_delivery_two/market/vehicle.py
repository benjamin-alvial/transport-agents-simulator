from typing import List


class Vehicle:
    """A vehicle owned by a courier.

    Attributes:
        vehicle_type: Category of the vehicle (e.g. "car", "bike").
        travel_time_factor: Multiplier applied to base travel times (< 1 is faster).
        capacity: Maximum total weight this vehicle can carry.
        itinerary: Ordered list of edge IDs to traverse, set by Router.
    """

    def __init__(self, vehicle_type: str, travel_time_factor: float, capacity: int):
        self.vehicle_type = vehicle_type
        self.travel_time_factor = travel_time_factor
        self.capacity = capacity
        self.itinerary: List[int] = []

    def start_journey(self):
        """Begin the vehicle's delivery journey (to be implemented)."""
        pass
