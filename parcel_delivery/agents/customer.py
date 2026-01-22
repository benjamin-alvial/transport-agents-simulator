from typing import TYPE_CHECKING

from parcel_delivery.agents.agent import Agent
from parcel_delivery.models.parcel import Parcel

if TYPE_CHECKING:
    from parcel_delivery.agents import Platform
    from parcel_delivery.simulation.message import Message


class Customer(Agent):
    """
    Agent that requests delivery of a Parcel.
    """
    def __init__(self, agent_id: str, location_node_id: int):
        super().__init__(agent_id)
        self.location_node_id: int = location_node_id

    def receive_message(self, message: "Message"):
        """
        Handle incoming messages. Customer doesn't receive messages.

        Args:
            message: The incoming message
        """
        pass

    def send_delivery_request(self, parcel: "Parcel", platform: "Platform"):
        """
        Requests the delivery of a Parcel to the specified Platform.

        Args:
            parcel: parcel being requested for delivery
            platform: platform being requested for delivery
        """

        if parcel.origin_node_id not in self.sim.network.nodes:
            raise ValueError("Node not in network, parcel cannot be delivered")
        if parcel.destination_node_id not in self.sim.network.nodes:
            raise ValueError("Node not in network, parcel cannot be delivered")

        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Sent DELIVERY_REQUEST for {parcel.contents} to {platform.agent_id}")
        self.send_message(receiver_id=platform.agent_id,
                          msg_type="DELIVERY_REQUEST",
                          content={"parcel": parcel},
                          delay=0.0)