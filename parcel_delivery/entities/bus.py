from typing import List, Optional, TYPE_CHECKING

from parcel_delivery.core.entity import Entity

if TYPE_CHECKING:
    from parcel_delivery.environment.edge import Edge


class Bus(Entity):
    """
    Represents a bus with a fixed timetable.
    """
    def __init__(self, entity_id: str, route: List[int]):
        super().__init__(entity_id)
        if len(route) < 2:
            raise ValueError("Bus route must contain at least two nodes")
        self.route: List[int] = route # List of node indices
        self.current_node: int = route[0] # Last node that was visited
        self.current_edge: Optional["Edge"] = None
        self.remaining_nodes: List[int] = self.route[1:] # Nodes left in the route to visit
        self.next_node: Optional[int] = None
        self.delay: float = 0.0
        self.vehicle_type: str = "bus"

    def get_delay(self) -> float:
        return self.delay

    def start_journey(self):
        """"
        Starts the journey of the bus through the nodes in its route.
        """
        # Already traveling
        if self.next_node is not None:
            return

        if not self.remaining_nodes:
            self.log_event_message(f"Journey of bus has ended!")
            return

        self.start_travel_to_next_node()

    def start_travel_to_next_node(self):
        """
        Begin travel to the next node in the route.
        """
        # Next node is just first in the remaining_nodes
        self.next_node = self.remaining_nodes[0]

        # Calculate travel time between current position and next stop location
        edge = self.sim.network.get_edge(self.current_node, self.next_node)
        if edge is None:
            raise RuntimeError(
                f"No edge between {self.current_node} and {self.next_node}"
            )
        travel_time = edge.get_travel_time()

        # Starts traveling
        self.log_event_message(f"Traveling through edge {edge}, will arrive in {travel_time:.5f}s")
        self.current_edge = edge
        self.current_edge.vehicle_enters(self, self.sim.current_time)
        self.schedule_action(travel_time, self.arrive_at_node, {"travel_time": travel_time})

    def arrive_at_node(self, travel_time: float):
        """"
        Bus arrives at a node.
        """
        # Exits edge
        self.current_edge.vehicle_exits(self, self.sim.current_time)
        self.current_edge = None

        # Update the bus's position and delay
        self.log_event_message(f"Arrived at {self.next_node}")
        self.current_node = self.next_node
        self.next_node = None
        self.delay += travel_time

        # Remove from remaining nodes to visit
        self.remaining_nodes.pop(0)

        # Continue to next destination
        self.start_journey()