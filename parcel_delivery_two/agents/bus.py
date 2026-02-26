from typing import List, Optional, TYPE_CHECKING

from parcel_delivery_two.agents.transport_vehicle import TransportVehicle

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel
    from parcel_delivery_two.environment.edge import Edge


class Bus(TransportVehicle):
    """A bus that follows a fixed sequence of nodes.

    The bus makes discrete-event hops between consecutive nodes in its route.
    The kernel injects itself via ``_kernel`` when this bus is registered via
    :meth:`~parcel_delivery_two.core.kernel.Kernel.register_entity`, enabling
    zero-argument DES scheduling of ``start_journey``.

    Attributes:
        entity_id: Unique identifier for this bus.
        route: Ordered list of node IDs defining the bus path.
    """

    def __init__(self, entity_id: str, route: List[int], travel_time_factor: float = 2.0):
        super().__init__(entity_id, travel_time_factor)
        self.route = route

    def start_journey(self) -> None:
        """Begin the bus journey along ``route``."""
        self._log_event(f"Starting journey with {max(0, len(self.route) - 1)} hops")
        self._schedule_hop(0)

    def _schedule_hop(self, index: int) -> None:
        """Schedule traversal of the hop from ``route[index]`` to ``route[index+1]``."""
        if index >= len(self.route) - 1:
            self._log_event("Journey complete")
            return
        from_node = self.route[index]
        to_node = self.route[index + 1]
        edge = self._find_edge(from_node, to_node)
        if edge is None:
            raise ValueError(
                f"Bus {self.entity_id}: no direct edge from node {from_node} to {to_node}"
            )
        self._log_edge(edge.edge_id, "entry")
        travel_time = self._compute_travel_time(edge)
        self._kernel.schedule(
            travel_time,
            lambda eid=edge.edge_id, idx=index: self._complete_hop(eid, idx),
        )

    def _complete_hop(self, edge_id: int, index: int) -> None:
        """Called when the bus finishes traversing one hop."""
        self._log_edge(edge_id, "exit")
        self._schedule_hop(index + 1)

    def _find_edge(self, from_node: int, to_node: int) -> Optional["Edge"]:
        """Return the first direct edge from *from_node* to *to_node*, or ``None``."""
        for edge in self._kernel.network.edges.values():
            if edge.from_node == from_node and edge.to_node == to_node:
                return edge
        return None
