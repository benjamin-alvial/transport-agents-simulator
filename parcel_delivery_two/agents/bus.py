from typing import List, TYPE_CHECKING

from parcel_delivery_two.agents.transport_vehicle import TransportVehicle

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel


class Bus(TransportVehicle):
    """A bus that follows a fixed sequence of edges.

    The kernel injects itself via ``_kernel`` when this bus is registered via
    :meth:`~parcel_delivery_two.core.kernel.Kernel.register_entity`, enabling
    zero-argument DES scheduling of ``start_journey``.

    Attributes:
        entity_id: Unique identifier for this bus.
        travel_time_factor: Multiplier applied to base travel times.
        itinerary: Ordered list of edge IDs defining the bus path.
    """

    def __init__(
        self,
        entity_id: str,
        itinerary: List[int],
        travel_time_factor: float = 2.0,
    ):
        super().__init__(entity_id, travel_time_factor, itinerary)
