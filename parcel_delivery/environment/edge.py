from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from parcel_delivery.loggers import EdgeLogger, AlertLogger
from parcel_delivery.models import Occupancy

if TYPE_CHECKING:
    from parcel_delivery import Entity, Bus, Courier


@dataclass
class Edge:
    """Represents a directed edge in the network with traffic attributes"""
    from_node: int
    to_node: int
    distance: float
    capacity: float = 10.0
    flow: float = 7.0
    base_speed: float = 27.78
    current_occupancies: Dict[str, "Occupancy"] = field(default_factory=dict)
    link_id: Optional[int] = None

    def __post_init__(self):
        self.historic_travel_times: List[float] = [self.distance/self.base_speed] * 96

    def get_travel_time_with_bpr(self) -> float:
        """
        Calculate travel time considering congestion using BPR function.
        """
        free_flow_time = self.distance / self.base_speed
        # BPR curve for congestion t_0*(1+alpha(q/Q)**beta)
        alpha = 0.15
        beta = 4
        delay = free_flow_time * (1 + alpha * (self.flow / self.capacity) ** beta)
        return delay

    def get_travel_time(self, sim_time_seconds: float) -> float:
        """Get historic travel time for a given simulation time in seconds."""
        slot = int(sim_time_seconds // 900) % 96
        return self.historic_travel_times[slot]

    def vehicle_enters(self, vehicle: "Entity", time: float):
        self.flow += 1
        EdgeLogger().log_entry(time, vehicle.entity_id, "entry", self.from_node, self.to_node, self.flow)

        if vehicle.vehicle_type == "bus":
            occ = Occupancy(vehicle.entity_id, "bus", time)
            self.current_occupancies[vehicle.entity_id] = occ

        if vehicle.vehicle_type == "courier":
            occ = Occupancy(vehicle.entity_id, "courier", time)
            self.current_occupancies[vehicle.entity_id] = occ
            # Generate alert if courier enters an edge occupied by a bus
            buses = [vid for vid, v in self.current_occupancies.items() if v.vehicle_type == "bus"]
            if buses:
                AlertLogger().log_entry(time, vehicle.entity_id, buses, self.from_node, self.to_node)

    def vehicle_exits(self, vehicle: "Entity", time: float):
        self.flow -= 1
        EdgeLogger().log_entry(time, vehicle.entity_id, "exit", self.from_node, self.to_node, self.flow)

        self.current_occupancies.pop(vehicle.entity_id)

    def congestion_ratio(self) -> float:
        """Returns flow/capacity ratio (0 to 1+)"""
        return self.flow / self.capacity if self.capacity > 0 else 0.0

    def is_congested(self, threshold: float = 0.8) -> bool:
        """Check if edge is above congestion threshold"""
        return self.congestion_ratio() > threshold

    def __repr__(self):
        return f"{self.from_node}->{self.to_node}"