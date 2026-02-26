from typing import List, Optional, TYPE_CHECKING

from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel
    from parcel_delivery_two.environment.edge import Edge


class Bus:
    """A bus that follows a fixed sequence of nodes.

    The bus makes discrete-event hops between consecutive nodes in its route.
    The kernel injects itself via ``_kernel`` when this bus is registered via
    :meth:`~parcel_delivery_two.core.kernel.Kernel.register_entity`, enabling
    zero-argument DES scheduling of ``start_journey``.

    Attributes:
        bus_id: Unique identifier for this bus.
        route: Ordered list of node IDs defining the bus path.
    """

    def __init__(self, bus_id: str, route: List[int]):
        self.bus_id = bus_id
        self.route = route
        self._kernel: Optional["Kernel"] = None

    def start_journey(self) -> None:
        """Begin the bus journey along ``route``.

        Logs a journey-start event and schedules discrete-event traversal of
        each hop between consecutive nodes. Must be called only after this bus
        has been registered with the kernel via
        :meth:`~parcel_delivery_two.core.kernel.Kernel.register_entity`.
        Does nothing meaningful when the route has fewer than two nodes.
        """
        EventLogger().log_entry(
            self._kernel.current_time,
            self.bus_id,
            f"Starting journey with {max(0, len(self.route) - 1)} hops",
        )
        self._schedule_hop(0)

    # ------------------------------------------------------------------
    # Internal DES helpers
    # ------------------------------------------------------------------

    def _schedule_hop(self, index: int) -> None:
        """Schedule traversal of the hop from ``route[index]`` to ``route[index+1]``.

        Logs a journey-complete event when all hops have been traversed.

        Args:
            index: Index of the departure node in ``self.route``. Logs
                completion and returns immediately when *index* is the last
                node (no more hops).

        Raises:
            ValueError: If no direct edge exists between the two consecutive
                route nodes.
        """
        if index >= len(self.route) - 1:
            EventLogger().log_entry(
                self._kernel.current_time,
                self.bus_id,
                "Journey complete",
            )
            return
        from_node = self.route[index]
        to_node = self.route[index + 1]
        edge = self._find_edge(from_node, to_node)
        if edge is None:
            raise ValueError(
                f"Bus {self.bus_id}: no direct edge from node {from_node} to {to_node}"
            )
        self._on_edge_entered(edge.edge_id)
        travel_time = self._travel_time(edge)
        self._kernel.schedule(
            travel_time,
            lambda eid=edge.edge_id, idx=index: self._complete_hop(eid, idx),
        )

    def _complete_hop(self, edge_id: int, index: int) -> None:
        """Called by the kernel when the bus finishes traversing one hop.

        Args:
            edge_id: The edge that was just traversed.
            index: The hop index (departure-node position) that just completed.
        """
        self._on_edge_exited(edge_id)
        self._schedule_hop(index + 1)

    def _find_edge(self, from_node: int, to_node: int) -> Optional["Edge"]:
        """Return the first direct edge from *from_node* to *to_node*, or ``None``.

        Args:
            from_node: Origin node ID.
            to_node: Destination node ID.

        Returns:
            The matching :class:`~parcel_delivery_two.environment.edge.Edge`,
            or ``None`` if no direct edge exists.
        """
        for edge in self._kernel.network.edges.values():
            if edge.from_node == from_node and edge.to_node == to_node:
                return edge
        return None

    def _travel_time(self, edge: "Edge") -> float:
        """Return the travel time for *edge* at the current simulation time.

        Uses the 15-minute historic travel-time bin keyed by seconds-since-
        midnight when available; falls back to free-flow otherwise.

        Args:
            edge: The edge to compute travel time for.

        Returns:
            Travel time in seconds.
        """
        bin_start = int(self._kernel.current_time // 900) * 900
        if bin_start in edge.travel_times:
            return edge.travel_times[bin_start]
        return edge.distance / edge.free_flow_speed

    def _on_edge_entered(self, edge_id: int) -> None:
        """Called when the bus begins traversing *edge_id*.

        Logs an ``"entry"`` event to :class:`~parcel_delivery_two.loggers.EdgeLogger`.

        Args:
            edge_id: The edge being entered.
        """
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self.bus_id,
            "entry",
            edge.from_node,
            edge.to_node,
        )

    def _on_edge_exited(self, edge_id: int) -> None:
        """Called when the bus finishes traversing *edge_id*.

        Logs an ``"exit"`` event to :class:`~parcel_delivery_two.loggers.EdgeLogger`.

        Args:
            edge_id: The edge being exited.
        """
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self.bus_id,
            "exit",
            edge.from_node,
            edge.to_node,
        )
