import heapq
from typing import Callable, List, Optional, TYPE_CHECKING, Union

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.loggers.base_logger import BaseLogger
from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing

if TYPE_CHECKING:
    from parcel_delivery_two.metrics.metrics_collector import MetricsCollector


class Kernel:
    """Discrete-event simulation engine.

    Maintains a priority-queue of (time, sequence, callable) events and
    advances the simulation clock as it processes them. Loggers are
    initialised via :meth:`initialize_loggers` and their CSVs are written
    automatically when :meth:`run` completes.

    Args:
        metrics_collector: Optional MetricsCollector instance to track
            simulation metrics. If provided, metrics will be saved to CSV
            and printed when the simulation ends.
    """

    def __init__(self, metrics_collector: Optional["MetricsCollector"] = None):
        self.current_time: float = 0.0
        self._event_queue: List[tuple] = []
        self._event_counter: int = 0
        self.network: Optional[Network] = None
        self._entities: list = []
        self.loggers: List[BaseLogger] = []
        self.metrics_collector: Optional["MetricsCollector"] = metrics_collector
        self.restrictions: List[Union[ProhibitEdge, CongestionPricing]] = []
        self._couriers: dict = {}

    def initialize_loggers(self) -> None:
        """Instantiate and register the default set of loggers.

        Attaches one :class:`~parcel_delivery_two.loggers.EdgeLogger` and one
        :class:`~parcel_delivery_two.loggers.EventLogger`. Their CSV files are
        written when :meth:`run` finishes.
        """
        self.loggers.append(EdgeLogger())
        self.loggers.append(EventLogger())

    def set_network(self, network: Network) -> None:
        """Store the road network for the simulation.

        Args:
            network: The Network instance to attach.
        """
        self.network = network

    def set_restrictions(self, restrictions: List[Union[ProhibitEdge, CongestionPricing]]) -> None:
        """Store the restrictions for the simulation.

        Args:
            restrictions: List of restrictions (ProhibitEdge or CongestionPricing).
        """
        self.restrictions = restrictions

    def register_courier(self, courier: Courier) -> None:
        """Register a courier entity with the kernel.

        Injects this kernel into every vehicle in the courier's fleet and
        assigns each vehicle a log-friendly ``entity_id`` of the form
        ``"<courier_id>_<vehicle_type>_<index>"``.

        Args:
            courier: The Courier to register.
        """
        self._entities.append(courier)
        self._couriers[courier.courier_id] = courier
        for i, vehicle in enumerate(courier.vehicles):
            vehicle._kernel = self
            vehicle.entity_id = f"{courier.courier_id}_{vehicle.vehicle_type}_{i}"

    def get_courier(self, courier_id: str) -> Optional[Courier]:
        """Get a courier by ID.

        Args:
            courier_id: The courier ID to look up.

        Returns:
            The Courier instance if found, None otherwise.
        """
        return self._couriers.get(courier_id)

    def register_entity(self, entity) -> None:
        """Register any entity with the kernel.

        Injects this kernel into the entity so that ``entity.start_journey``
        can schedule DES events.

        Args:
            entity: The entity to register.
        """
        self._entities.append(entity)
        entity._kernel = self

    def schedule(self, delay: float, action: Callable) -> None:
        """Schedule an action to fire after *delay* simulation seconds.

        Args:
            delay: Non-negative offset from current_time.
            action: Zero-argument callable to invoke when the event fires.

        Raises:
            ValueError: If delay is negative.
        """
        if delay < 0:
            raise ValueError(f"Delay must be non-negative, got {delay}")
        fire_at = self.current_time + delay
        heapq.heappush(self._event_queue, (fire_at, self._event_counter, action))
        self._event_counter += 1

    def run(self, until: float) -> None:
        """Process events until the queue is empty or *until* is reached.

        After the event loop finishes, all registered loggers write their
        accumulated entries to CSV. If a metrics_collector is set, metrics
        are also saved and printed.

        Args:
            until: Absolute simulation time at which to stop.
        """
        while self._event_queue:
            fire_at, _, action = self._event_queue[0]
            if fire_at > until:
                break
            heapq.heappop(self._event_queue)
            self.current_time = fire_at
            action()
        self.current_time = until
        for logger in self.loggers:
            logger.dump_to_csv()
        if self.metrics_collector is not None:
            self.metrics_collector.dump_to_csv()
            self.metrics_collector.print_summary()
