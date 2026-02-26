from typing import List, Optional, TYPE_CHECKING

from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger

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
    """

    def __init__(self, entity_id: str, travel_time_factor: float = 1.0):
        self.entity_id = entity_id
        self.travel_time_factor = travel_time_factor
        self._kernel: Optional["Kernel"] = None

    def _log_event(self, message: str) -> None:
        """Log a journey event."""
        EventLogger().log_entry(
            self._kernel.current_time,
            self.entity_id,
            message,
        )

    def _log_edge(self, edge_id: int, event_type: str) -> None:
        """Log an edge entry/exit event."""
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self.entity_id,
            event_type,
            edge.from_node,
            edge.to_node,
        )

    def _compute_travel_time(self, edge: "Edge") -> float:
        """Return travel time for edge, scaled by travel_time_factor."""
        bin_start = int(self._kernel.current_time // 900) * 900
        if bin_start in edge.travel_times:
            return edge.travel_times[bin_start] * self.travel_time_factor
        return (edge.distance / edge.free_flow_speed) * self.travel_time_factor
