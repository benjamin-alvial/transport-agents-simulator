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

    def start_journey(self) -> None:
        """Begin the vehicle's delivery journey along its itinerary."""
        self._log_event(f"Starting journey with {len(self.itinerary)} edges")
        self._schedule_edge(0)

    def _schedule_edge(self, index: int) -> None:
        """Schedule traversal of the edge at *index* in the itinerary."""
        if index >= len(self.itinerary):
            self._log_event("Journey complete")
            return
        edge_id = self.itinerary[index]
        self._log_edge(edge_id, "entry")
        edge = self._kernel.network.edges[edge_id]
        travel_time = self._compute_travel_time(edge)
        self._kernel.schedule(
            travel_time,
            lambda eid=edge_id, idx=index: self._complete_edge(eid, idx),
        )

    def _complete_edge(self, edge_id: int, index: int) -> None:
        """Called when the vehicle finishes traversing one edge."""
        self._log_edge(edge_id, "exit")
        self._schedule_edge(index + 1)
