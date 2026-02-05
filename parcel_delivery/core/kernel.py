import heapq
from typing import List, Dict, Optional, Callable, Any

from parcel_delivery.core.agent import Agent
from parcel_delivery.core.entity import Entity
from parcel_delivery.core.event import Event
from parcel_delivery.core.message import Message
from parcel_delivery.environment.network import Network


class Kernel:
    """
    The simulation DES engine. Manages the event queue and simulation clock and keeps track of entities.
    """

    def __init__(self):
        self.current_time: float = 6*60*60 # Begin at 6:00 in the morning
        self.event_queue: List["Event"] = []
        self.event_counter: int = 0
        self.running: bool = False
        self.entities: Dict[str, "Entity"] = {}
        self.network: Optional["Network"] = None

    def register_entity(self, entity: "Entity"):
        """
        Register an entity within the core.

        Args:
            entity: The entity to be registered
        """
        if entity.entity_id in self.entities:
            raise ValueError(f"Entity {entity.entity_id} already registered")
        self.entities[entity.entity_id] = entity
        entity.sim = self

    def get_entity(self, entity_id: str) -> Optional["Entity"]:
        """
        Retrieve an entity by ID.

        Args:
            entity_id: The entity ID of the entity to be retrieved

        Returns:
            The retrieved entity object
        """
        return self.entities.get(entity_id)

    def set_network(self, network: "Network"):
        """Set the road network for the simulation"""
        self.network = network

    def schedule(self, delay: float, action: Callable, data: dict[str, Any] | None = None) -> "Event":
        """
        Schedule an event to occur after 'delay' time units.

        Args:
            delay: Time from now when event should occur (must be >= 0)
            action: Function to call when event fires
            data: Optional dictionary of parameters to pass to action

        Returns:
            The scheduled Event object
        """
        if delay < 0:
            raise ValueError(f"Delay must be non-negative, got {delay}")

        event_time = self.current_time + delay
        event = Event(
            time=event_time,
            event_id=self.event_counter,
            action=action,
            data=data or {}
        )
        self.event_counter += 1
        heapq.heappush(self.event_queue, event)  # type: ignore
        return event

    def schedule_at(self, time: float, action: Callable, data: dict[str, Any] | None = None) -> "Event":
        """
        Schedule an event to occur at a specific absolute time.

        Args:
            time: Absolute core time for the event
            action: Function to call when event fires
            data: Optional dictionary of parameters to pass to action

        Returns:
            The scheduled Event object
        """
        if time < self.current_time:
            raise ValueError(f"Cannot schedule event in the past: {time} < {self.current_time}")

        event = Event(
            time=time,
            event_id=self.event_counter,
            action=action,
            data=data or {}
        )
        self.event_counter += 1
        heapq.heappush(self.event_queue, event)  # type: ignore
        return event

    def send_message(self, sender_id: str, receiver_id: str,
                     msg_type: str, content: Any, delay: float = 0.0):
        """
        Send a message from one agent to another with optional delay.

        Args:
            sender_id: ID of sending agent
            receiver_id: ID of receiving agent
            msg_type: Type of message (e.g., 'DELIVERY_REQUEST', 'BID_REQUEST')
            content: Message payload (dictionary with variable names as keys)
            delay: Delivery delay (default 0 for instant)
        """
        sender = self.get_entity(sender_id)
        if sender is None:
            raise ValueError(f"Agent {sender_id} not found")

        receiver = self.get_entity(receiver_id)
        if receiver is None:
            raise ValueError(f"Agent {receiver_id} not found")

        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            msg_type=msg_type,
            content=content,
            timestamp=self.current_time
        )

        # Schedule message delivery
        if isinstance(receiver, Agent):
            self.schedule(delay, receiver.receive_message, {"message": message})

    def run(self, until: Optional[float] = None):
        """
        Run the simulation until the event queue is empty or 'until' time is reached.

        Args:
            until: Optional stop time. If None, runs until queue is empty.
        """
        self.running = True

        while self.running and self.event_queue:
            # Peek at next event
            next_event = self.event_queue[0]

            # Check if we've reached the stop time
            if until is not None and next_event.time > until:
                self.current_time = until
                break

            # Pop and execute the event
            event = heapq.heappop(self.event_queue)  # type: ignore
            self.current_time = event.time
            event.execute()

        # If we stopped early due to 'until', update time
        if until is not None and self.current_time < until:
            self.current_time = until

    def stop(self):
        """Stop the simulation (can be called from within an event)"""
        self.running = False

    def peek_next_event_time(self) -> Optional[float]:
        """Return the time of the next event without removing it"""
        return self.event_queue[0].time if self.event_queue else None

    def reset(self):
        """Reset the simulation to initial state"""
        self.current_time = 0.0
        self.event_queue = []
        self.event_counter = 0
        self.running = False
        self.entities = {}