from typing import List, TYPE_CHECKING

from parcel_delivery_two.agents.transport_vehicle import TransportVehicle

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel


class CourierVehicle(TransportVehicle):
    """A vehicle owned by a courier for making deliveries.

    After routing, ``itinerary`` holds the ordered edge IDs to traverse.
    The kernel injects itself via ``_kernel`` when the owning courier is
    registered, enabling zero-argument DES scheduling of ``start_journey``.

    Attributes:
        vehicle_type: Category of the vehicle (e.g. ``"car"``, ``"bike"``).
        travel_time_factor: Multiplier applied to base travel times.
        capacity: Maximum total weight this vehicle can carry.
        itinerary: Ordered list of edge IDs to traverse, set by Router.
    """

    def __init__(
        self,
        vehicle_type: str,
        travel_time_factor: float,
        capacity: int,
    ):
        entity_id = f"{vehicle_type}_vehicle"
        super().__init__(entity_id, travel_time_factor)
        self.vehicle_type = vehicle_type
        self.capacity = capacity
        self.itinerary: List[int] = []
