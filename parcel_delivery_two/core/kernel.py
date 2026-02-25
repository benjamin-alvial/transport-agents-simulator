import heapq
from typing import Callable, List, Optional

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.market.courier import Courier


class Kernel:
    """Discrete-event simulation engine.

    Maintains a priority-queue of (time, sequence, callable) events and
    advances the simulation clock as it processes them.
    """

    def __init__(self):
        self.current_time: float = 0.0
        self._event_queue: List[tuple] = []
        self._event_counter: int = 0
        self.network: Optional[Network] = None
        self._entities: list = []

    def initialize_loggers(self):
        """No-op placeholder for logger initialisation."""
        pass

    def set_network(self, network: Network):
        """Store the road network for the simulation.

        Args:
            network: The Network instance to attach.
        """
        self.network = network

    def register_courier(self, courier: Courier):
        """Register a courier entity with the kernel.

        Args:
            courier: The Courier to register.
        """
        self._entities.append(courier)

    def register_entity(self, entity):
        """Register any entity with the kernel.

        Args:
            entity: The entity to register.
        """
        self._entities.append(entity)

    def schedule(self, delay: float, action: Callable):
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

    def run(self, until: float):
        """Process events until the queue is empty or *until* is reached.

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
