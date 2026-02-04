from parcel_delivery.core.agent import Agent
from parcel_delivery.core.message import Message
from parcel_delivery.models.parcel import Parcel
from parcel_delivery.entities.platform import Platform


class Customer(Agent):
    """
    Agent that requests delivery of a parcel.
    """
    def __init__(self, entity_id: str, location_node_id: int):
        super().__init__(entity_id)
        self.location_node_id: int = location_node_id

    def receive_message(self, message: "Message"):
        """
        Handle incoming message.

        Args:
            message: The incoming message
        """
        raise NotImplementedError

    def send_delivery_request(self, parcel: "Parcel", platform: "Platform"):
        """
        Requests the delivery of a parcel to the specified platform.

        Args:
            parcel: The parcel being requested for delivery
            platform: The platform to with the request is submitted
        """

        if parcel.origin_node_id not in self.sim.network.nodes:
            raise ValueError("Parcel's origin node not in network, parcel cannot be delivered")
        if parcel.destination_node_id not in self.sim.network.nodes:
            raise ValueError("Parcel's destination node not in network, parcel cannot be delivered")

        print(f"[t={self.sim.current_time:.1f}] {self.entity_id}: Sent DELIVERY_REQUEST for {parcel.contents} to {platform.entity_id}")
        self.send_message(receiver_id=platform.entity_id,
                          msg_type="DELIVERY_REQUEST",
                          content={"parcel": parcel},
                          delay=0.0)