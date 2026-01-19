from typing import Dict

from parcel_delivery.agents import Agent
from parcel_delivery.models import Parcel


class Platform(Agent):
    """
    Agent that generates auctions for parcel delivery.
    It receives Customers' parcel delivery requests and assigns them to Couriers.
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.parcel_count: int = 0
        self.parcels: Dict[str, Parcel] = {}

    def initialize_deliveries(self, parcels: list):
        """
        Initializes list of initial parcel deliveries, assigning an index to each.

        Args:
            parcels: List of initial parcels
        """
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Deliveries have been initialized")
        for parcel in parcels:
            parcel.id = str(self.parcel_count)
            self.parcel_count += 1
            self.parcels[parcel.id] = parcel

    def receive_parcel_request(self, parcel: Parcel):
        """
        The requested parcel delivery is added to the list of deliveries.

        Args:
            parcel: parcel being requested for delivery
        """
        parcel.id = str(self.parcel_count)
        self.parcel_count += 1
        self.parcels[parcel.id] = parcel

    def query_parcels(self):
        """
        Returns the current list of parcel deliveries.

        Returns:
            parcels: Dictionary of parcel deliveries
        """

        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Current deliveries are communicated")
        for parcel in self.parcels.values():
            print(parcel)
        return self.parcels.values()


    def assign_parcel(self, parcel: Parcel) -> bool:
        """
        Gives permission for courier to add parcel to vehicle.

        Args:
            parcel: parcel being requested for delivery

        Returns:
            true if parcel has been assigned to courier, false otherwise
        """
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Parcel with {parcel.contents} assigned to courier")
        return True