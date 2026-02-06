from dataclasses import dataclass
from typing import TYPE_CHECKING

from parcel_delivery.loggers import EdgeLogger

if TYPE_CHECKING:
    from parcel_delivery import Entity


@dataclass
class Edge:
    """Represents a directed edge in the network with traffic attributes"""
    from_node: int
    to_node: int
    distance: float
    capacity: float = 10.0
    flow: float = 7.0

    def get_travel_time(self, base_speed: float = 14.0) -> float:
        """
        Calculate travel time considering congestion using BPR function.

        Args:
            base_speed: Free-flow speed in m/s

        Returns:
            Travel time in hours
        """
        free_flow_time = self.distance / base_speed
        # BPR curve for congestion t_0*(1+alpha(q/Q)**beta)
        alpha = 0.15
        beta = 4
        delay = free_flow_time * (1 + alpha * (self.flow / self.capacity) ** beta)
        return delay

    def vehicle_enters(self, vehicle: "Entity", time: float):
        self.flow += 1
        EdgeLogger().log_entry(time, vehicle.entity_id, "entry", self.from_node, self.to_node, self.flow)

    def vehicle_exits(self, vehicle: "Entity", time: float):
        self.flow -= 1
        EdgeLogger().log_entry(time, vehicle.entity_id, "exit", self.from_node, self.to_node, self.flow)

    def congestion_ratio(self) -> float:
        """Returns flow/capacity ratio (0 to 1+)"""
        return self.flow / self.capacity if self.capacity > 0 else 0.0

    def is_congested(self, threshold: float = 0.8) -> bool:
        """Check if edge is above congestion threshold"""
        return self.congestion_ratio() > threshold

    def __repr__(self):
        return f"{self.from_node}->{self.to_node}"