import heapq
from typing import Callable, List, Optional

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.loggers.base_logger import BaseLogger
from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger
from parcel_delivery_two.market.courier import Courier


class Kernel:
    """Discrete-event simulation engine.

    Maintains a priority-queue of (time, sequence, callable) events and
    advances the simulation clock as it processes them. Loggers are
    initialised via :meth:`initialize_loggers` and their CSVs are written
    automatically when :meth:`run` completes.
    """

    def __init__(self):
        self.current_time: float = 0.0
        self._event_queue: List[tuple] = []
        self._event_counter: int = 0
        self.network: Optional[Network] = None
        self._entities: list = []
        self.loggers: List[BaseLogger] = []

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

    def register_courier(self, courier: Courier) -> None:
        """Register a courier entity with the kernel.

        Injects this kernel into every vehicle in the courier's fleet and
        assigns each vehicle a log-friendly ``_entity_id`` of the form
        ``"<courier_id>_<vehicle_type>_<index>"``.

        Args:
            courier: The Courier to register.
        """
        self._entities.append(courier)
        for i, vehicle in enumerate(courier.vehicles):
            vehicle._kernel = self
            vehicle._entity_id = f"{courier.courier_id}_{vehicle.vehicle_type}_{i}"

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
        accumulated entries to CSV.

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
