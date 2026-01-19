import heapq
from typing import List, Dict, Optional, Callable, Any, TYPE_CHECKING

from parcel_delivery.agents.agent import Agent
from parcel_delivery.simulation.event import Event
from parcel_delivery.simulation.message import Message


class Kernel:
    """
    The core DES engine. Manages the event queue and simulation clock and keeps track of agents.
    """

    def __init__(self):
        self.current_time: float = 0.0
        self.event_queue: List["Event"] = []
        self.event_counter: int = 0
        self.running: bool = False
        self.agents: Dict[str, "Agent"] = {}

    def register_agent(self, agent: "Agent"):
        """
        Register an agent within the simulation.

        Args:
            agent: The agent to be registered
        """
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent {agent.agent_id} already registered")
        self.agents[agent.agent_id] = agent
        agent.sim = self

    def get_agent(self, agent_id: str) -> Optional["Agent"]:
        """
        Retrieve an agent by ID.

        Args:
            agent_id: Agent ID of the agent to be retrieved

        Returns:
            The retrieved agent object
        """
        return self.agents.get(agent_id)

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
            time: Absolute simulation time for the event
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
            msg_type: Type of message (e.g., 'offer', 'accept', 'reject')
            content: Message payload
            delay: Delivery delay (default 0 for instant)
        """
        sender = self.get_agent(sender_id)
        if sender is None:
            raise ValueError(f"Agent {sender_id} not found")

        receiver = self.get_agent(receiver_id)
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
        self.agents = {}