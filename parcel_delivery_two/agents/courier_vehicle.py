from typing import List, TYPE_CHECKING

from parcel_delivery_two.agents.transport_vehicle import TransportVehicle
from parcel_delivery_two.loggers.event_logger import EventLogger
from parcel_delivery_two.metrics.metrics_collector import MetricsCollector

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel
    from parcel_delivery_two.market.delivery_request import DeliveryRequest


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
        assigned_requests: List of delivery requests assigned to this vehicle.
        _destination_nodes: Set of node IDs where deliveries should be made.
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
        self.assigned_requests: List["DeliveryRequest"] = []
        self._destination_nodes: set = set()

    def _complete_edge(self, edge_id: int, index: int, travel_time: float) -> None:
        """Called when the vehicle finishes traversing one edge.

        Logs delivery events when arriving at destination nodes.
        """
        super()._complete_edge(edge_id, index, travel_time)

        # Check if we've arrived at a delivery destination
        edge = self._kernel.network.edges[edge_id]
        current_node = edge.to_node

        if current_node in self._destination_nodes:
            # Find and log the delivery request(s) for this destination
            for req in self.assigned_requests:
                if req.destination == current_node:
                    EventLogger().log_entry(
                        self._kernel.current_time,
                        self.entity_id,
                        f"Delivered parcel '{req.name}' to node {current_node}",
                    )
                    MetricsCollector().record_delivery_completion()
