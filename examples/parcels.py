from dataclasses import dataclass
from typing import Dict, List, Optional

from des import SimulationKernel, Agent


class Platform(Agent):
    """
    Agent that generates auctions for parcel delivery.
    It receives Customers' parcel delivery requests and assigns them to Couriers.
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.parcel_count: int = 0
        self.parcels: Dict[str, "Parcel"] = {}

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

    def receive_parcel_request(self, parcel: "Parcel"):
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


    def request_parcel(self, parcel:"Parcel"):
        """
        Gives permission for courier to add parcel to vehicle.

        Args:
            parcel: parcel being requested for delivery
        """
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Parcel with {parcel.contents} assigned to courier")
        parcel.state = "being_delivered"


class Customer(Agent):
    """
    Agent that requests delivery of a Parcel.
    """
    def __init__(self, agent_id: str, location: int):
        super().__init__(agent_id)
        self.location = location

    def request_delivery(self, parcel: "Parcel", platform: "Platform"):
        """
        Requests the delivery of a Parcel to the specified Platform.

        Args:
            parcel: parcel being requested for delivery
            platform: platform being requested for delivery
        """

        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Sent delivery request notification for {parcel.contents}")
        platform.receive_parcel_request(parcel)


class Courier(Agent):
    """
    Agent that delivers Parcels.
    """

    def __init__(self, agent_id: str, location: int, capacity: int):
        super().__init__(agent_id)
        self.location: int = location
        self.capacity: int = capacity
        self.schedule: Optional[List[int]] = None
        self.current_load: float = 0
        self.carried_parcels: List[Parcel] = []

    def ask_for_parcels(self, platform: "Platform"):
        """
        Queries to the Platform for all Parcels available for delivery
        and requests the delivery of all those that fit.

        Args:
            platform: platform that has all Parcels
        """

        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Sent parcels request notification to {platform.agent_id}")
        available_parcels = platform.query_parcels()
        for parcel in available_parcels:
            if parcel.state == "waiting_pick_up":
                if self.current_load + parcel.weight <= self.capacity:
                    print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Requests to add {parcel.contents} parcel to vehicle")
                    platform.request_parcel(parcel)
                    self.carried_parcels.append(parcel)


@dataclass
class Parcel:
    """
    A parcel that can be delivered.
    """
    contents: str
    location: int
    deadline: float
    weight: float
    fare: float
    id: Optional[str] = None
    state: str = "waiting_pick_up"


if __name__ == "__main__":
    sim = SimulationKernel()

    # Create agents
    uber = Platform("uber")
    customer_sending = Customer("customer_sending", 10)
    customer_receiving = Customer("customer_receiving", 210)
    courier = Courier("courier", 0, 20)

    sim.register_agent(uber)
    sim.register_agent(customer_sending)
    sim.register_agent(customer_receiving)
    sim.register_agent(courier)

    # Define already existing to-be-delivered parcels in the platform
    sample_parcel_1 = Parcel("socks", 120, 100, 0.5, 10)
    sample_parcel_2 = Parcel("books", 120, 100, 4, 10)
    sim.schedule(1.0, lambda _: uber.initialize_deliveries(
        parcels=[sample_parcel_1, sample_parcel_2],
    ), None)

    sim.schedule(5.0, lambda _: customer_sending.request_delivery(
        Parcel("laptop", 10, 200, 5, 10),
        uber
    ), None)

    sim.schedule(10.0, lambda _: courier.ask_for_parcels(uber), None)


    print("Starting simulation...\n")
    sim.run(until=20.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")