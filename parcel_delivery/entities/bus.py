from typing import List

from parcel_delivery import Entity


class Bus(Entity):
    """
    Represents a bus with a fixed timetable.
    """
    def __init__(self, entity_id: str, route: List[int]):
        super().__init__(entity_id)
        self.route: List[int] = route # List of node indices
        self.current_node: int = route[0] # Last node that was visited
        self.remaining_nodes: List[int] = self.route[1:] # Nodes left in the route to visit

    def start_journey(self):
        """"
        Starts the journey of the bus through the nodes in its route.
        """
        if not self.remaining_nodes:
            self.print_log_message(f"Journey of bus has ended!")

        else:
            # Next node is just first in the remaining_nodes
            next_node = self.remaining_nodes[0]

            # Calculate travel time between current position and next stop location
            edge = self.sim.network.get_edge(self.current_node, next_node)
            travel_time = edge.get_travel_time()

            # Starts traveling
            self.print_log_message(f"Traveling through edge {edge}, will arrive in {travel_time:.5f}s")
            self.schedule_action(travel_time, self.arrive_at_node, {"next_node": next_node})

    def arrive_at_node(self, next_node: int):
        """"
        Bus arrives at a node.
        """
        # Update the bus's position
        self.print_log_message(f"Arrived at {next_node}")
        self.current_node = next_node

        # Remove from remaining nodes to visit
        self.remaining_nodes.pop(0)

        # Continue to next destination
        self.start_journey()