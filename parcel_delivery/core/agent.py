from abc import abstractmethod
from typing import Any

from parcel_delivery.core.message import Message
from parcel_delivery.core.entity import Entity


class Agent(Entity):
    """
    An entity that can communicate with other agents via messages.

    Agents make decisions and interact with each other through
    the message-passing system.

    Examples: Couriers (bid in auctions), Platform (runs auctions)
    """

    @abstractmethod
    def receive_message(self, message: "Message"):
        """
        Handle incoming messages. Must be implemented by subclasses.

        Args:
            message: The incoming message
        """
        pass

    def send_message(self, receiver_id: str, msg_type: str,
                     content: Any, delay: float = 0.0):
        """
        Send a message to another agent.

        Args:
            receiver_id: ID of receiving agent
            msg_type: Type of message
            content: Message payload, usually a dictionary with variable names as keys
            delay: Delivery delay
        """
        if self.sim is None:
            raise RuntimeError(f"Agent {self.entity_id} not registered with core")
        self.sim.send_message(self.entity_id, receiver_id, msg_type, content, delay)