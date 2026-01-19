from typing import TYPE_CHECKING

from parcel_delivery.agents import Agent
from parcel_delivery.models import Parcel

if TYPE_CHECKING:
    from parcel_delivery.agents import Platform


class Customer(Agent):
    """
    Agent that requests delivery of a Parcel.
    """
    def __init__(self, agent_id: str, location: int):
        super().__init__(agent_id)
        self.location = location

    def request_delivery(self, parcel: Parcel, platform: "Platform"):
        """
        Requests the delivery of a Parcel to the specified Platform.

        Args:
            parcel: parcel being requested for delivery
            platform: platform being requested for delivery
        """

        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Sent delivery request notification for {parcel.contents}")
        platform.receive_parcel_request(parcel)