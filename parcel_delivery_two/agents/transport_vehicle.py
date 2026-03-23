from typing import List, Optional, TYPE_CHECKING

from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger
from parcel_delivery_two.metrics.metrics_collector import MetricsCollector
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel
    from parcel_delivery_two.environment.edge import Edge


class TransportVehicle:
    """Base class for vehicles that travel through the network.

    The kernel injects itself via ``_kernel`` (and a log-friendly
    ``entity_id``) when the entity is registered, enabling zero-argument
    DES scheduling of ``start_journey``.

    Attributes:
        entity_id: Unique identifier for this vehicle.
        travel_time_factor: Multiplier applied to base travel times.
        itinerary: Ordered list of edge IDs to traverse.
    """

    def __init__(
        self,
        entity_id: str,
        travel_time_factor: float = 1.0,
        itinerary: list = None,
    ):
        self.entity_id = entity_id
        self.travel_time_factor = travel_time_factor
        self.itinerary = itinerary if itinerary is not None else []
        self._kernel: Optional["Kernel"] = None

    def start_journey(self) -> None:
        """Begin the journey along the itinerary."""
        self._log_event(f"Starting journey with {len(self.itinerary)} edges")
        self._advance(0)

    def _advance(self, index: int) -> None:
        """Schedule traversal of the edge at *index* in the itinerary."""
        if index >= len(self.itinerary):
            self._log_event("Journey complete")
            return
        edge_id = self.itinerary[index]
        self._on_edge_entered(edge_id)
        edge = self._kernel.network.edges[edge_id]
        travel_time = self._compute_travel_time(edge)
        self._kernel.schedule(
            travel_time,
            lambda eid=edge_id, idx=index, tt=travel_time: self._complete_edge(eid, idx, tt),
        )

    def _complete_edge(self, edge_id: int, index: int, travel_time: float) -> None:
        """Called when the vehicle finishes traversing one edge."""
        self._on_edge_exited(edge_id)
        edge = self._kernel.network.edges[edge_id]
        monetary_cost = self._compute_edge_cost(edge_id)
        MetricsCollector().record_edge_completion(
            self.entity_id, edge.distance, travel_time, monetary_cost
        )
        self._advance(index + 1)

    def _compute_edge_cost(self, edge_id: int) -> float:
        """Calculate monetary cost for traversing an edge.

        Computes congestion pricing costs based on the vehicle's courier VTT
        and any applicable CongestionPricing restrictions.

        Args:
            edge_id: The ID of the edge being traversed.

        Returns:
            Monetary cost in dollars for traversing the edge.
        """
        # Parse entity_id to get courier_id and vehicle_type
        # Format: "{courier_id}_{vehicle_type}_{index}" for courier vehicles
        parts = self.entity_id.split("_")
        if len(parts) < 3:
            # Not a courier vehicle (e.g., bus), no congestion pricing
            return 0.0

        courier_id = parts[0]
        vehicle_type = parts[1]

        # Get courier's VTT
        courier = self._kernel.get_courier(courier_id)
        if courier is None or courier.vtt <= 0:
            return 0.0

        # Calculate congestion cost from applicable restrictions
        current_time = self._kernel.current_time
        total_cost = 0.0

        for restriction in self._kernel.restrictions:
            if isinstance(restriction, CongestionPricing):
                if restriction.edge_id == edge_id:
                    total_cost += restriction.get_cost(vehicle_type, current_time)

        return total_cost

    def _log_event(self, message: str) -> None:
        """Log a journey event."""
        EventLogger().log_entry(
            self._kernel.current_time,
            self.entity_id,
            message,
        )

    def _on_edge_entered(self, edge_id: int) -> None:
        """Called when the vehicle begins traversing *edge_id*."""
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self.entity_id,
            "entry",
            edge.from_node,
            edge.to_node,
        )

    def _on_edge_exited(self, edge_id: int) -> None:
        """Called when the vehicle finishes traversing *edge_id*."""
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self.entity_id,
            "exit",
            edge.from_node,
            edge.to_node,
        )

    def _compute_travel_time(self, edge: "Edge") -> float:
        """Return travel time for edge, scaled by travel_time_factor."""
        bin_start = int(self._kernel.current_time // 900) * 900
        if bin_start in edge.travel_times:
            return edge.travel_times[bin_start] * self.travel_time_factor
        return (edge.distance / edge.free_flow_speed) * self.travel_time_factor
