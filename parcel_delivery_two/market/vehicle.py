from typing import List, Optional, TYPE_CHECKING

from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger

if TYPE_CHECKING:
    from parcel_delivery_two.core.kernel import Kernel
    from parcel_delivery_two.environment.edge import Edge


class Vehicle:
    """A vehicle owned by a courier.

    After routing, ``itinerary`` holds the ordered edge IDs to traverse.
    The kernel injects itself via ``_kernel`` (and a log-friendly
    ``_entity_id``) when the owning courier is registered, enabling
    zero-argument DES scheduling of ``start_journey``.

    Attributes:
        vehicle_type: Category of the vehicle (e.g. ``"car"``, ``"bike"``).
        travel_time_factor: Multiplier applied to base travel times
            (values below 1 make the vehicle faster).
        capacity: Maximum total weight this vehicle can carry.
        itinerary: Ordered list of edge IDs to traverse, set by Router.
    """

    def __init__(self, vehicle_type: str, travel_time_factor: float, capacity: int):
        self.vehicle_type = vehicle_type
        self.travel_time_factor = travel_time_factor
        self.capacity = capacity
        self.itinerary: List[int] = []
        self._kernel: Optional["Kernel"] = None
        self._entity_id: str = "unregistered"

    def start_journey(self) -> None:
        """Begin the vehicle's delivery journey along its itinerary.

        Logs a journey-start event and schedules discrete-event traversal
        of each edge in ``itinerary`` using the attached kernel. Does nothing
        meaningful when the itinerary is empty. Must be called only after the
        owning courier has been registered with the kernel.
        """
        EventLogger().log_entry(
            self._kernel.current_time,
            self._entity_id,
            f"Starting journey with {len(self.itinerary)} edges",
        )
        self._schedule_edge(0)

    # ------------------------------------------------------------------
    # Internal DES helpers
    # ------------------------------------------------------------------

    def _schedule_edge(self, index: int) -> None:
        """Schedule traversal of the edge at position *index* in the itinerary.

        Logs a journey-complete event when all edges have been traversed.

        Args:
            index: Position in ``self.itinerary``. Logs completion and returns
                immediately when *index* is out of range.
        """
        if index >= len(self.itinerary):
            EventLogger().log_entry(
                self._kernel.current_time,
                self._entity_id,
                "Journey complete",
            )
            return
        edge_id = self.itinerary[index]
        edge = self._kernel.network.edges[edge_id]
        self._on_edge_entered(edge_id)
        travel_time = self._travel_time(edge)
        self._kernel.schedule(
            travel_time,
            lambda eid=edge_id, idx=index: self._complete_edge(eid, idx),
        )

    def _complete_edge(self, edge_id: int, index: int) -> None:
        """Called by the kernel when the vehicle finishes traversing one edge.

        Args:
            edge_id: The edge that was just traversed.
            index: Its position in the itinerary.
        """
        self._on_edge_exited(edge_id)
        self._schedule_edge(index + 1)

    def _travel_time(self, edge: "Edge") -> float:
        """Return the travel time for *edge* at the current simulation time.

        Uses the 15-minute historic travel-time bin keyed by seconds-since-
        midnight when available; falls back to free-flow otherwise.

        Args:
            edge: The edge to compute travel time for.

        Returns:
            Travel time in seconds, scaled by ``travel_time_factor``.
        """
        bin_start = int(self._kernel.current_time // 900) * 900
        if bin_start in edge.travel_times:
            return edge.travel_times[bin_start] * self.travel_time_factor
        return (edge.distance / edge.free_flow_speed) * self.travel_time_factor

    def _on_edge_entered(self, edge_id: int) -> None:
        """Called when the vehicle begins traversing *edge_id*.

        Logs an ``"entry"`` event to :class:`~parcel_delivery_two.loggers.EdgeLogger`.

        Args:
            edge_id: The edge being entered.
        """
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self._entity_id,
            "entry",
            edge.from_node,
            edge.to_node,
        )

    def _on_edge_exited(self, edge_id: int) -> None:
        """Called when the vehicle finishes traversing *edge_id*.

        Logs an ``"exit"`` event to :class:`~parcel_delivery_two.loggers.EdgeLogger`.

        Args:
            edge_id: The edge being exited.
        """
        edge = self._kernel.network.edges[edge_id]
        EdgeLogger().log_entry(
            self._kernel.current_time,
            self._entity_id,
            "exit",
            edge.from_node,
            edge.to_node,
        )
