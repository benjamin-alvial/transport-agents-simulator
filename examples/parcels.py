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


    def assign_parcel(self, parcel:"Parcel") -> bool:
        """
        Gives permission for courier to add parcel to vehicle.

        Args:
            parcel: parcel being requested for delivery

        Returns:
            true if parcel has been assigned to courier, false otherwise
        """
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Parcel with {parcel.contents} assigned to courier")
        return True


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

class Stop:
    """Represents a stop on the courier's route"""

    def __init__(self, location: int, type: str, parcel: "Parcel"):
        self.location: int = location
        self.type: str = type
        self.parcel: "Parcel" = parcel

class Courier(Agent):
    """
    Agent that delivers Parcels.
    """

    def __init__(self, agent_id: str, position: int, capacity: int, speed: float):
        super().__init__(agent_id)
        self.position: int = position
        self.capacity: int = capacity
        self.speed: float = speed
        self.schedule: List[Stop] = []
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

        # Courier tries to request all parcels that fit in its capacity
        for parcel in available_parcels:
            if parcel.state == "waiting_pick_up":
                if self.current_load + parcel.weight <= self.capacity:
                    print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Requests to add {parcel.contents} parcel to vehicle")
                    assigned = platform.assign_parcel(parcel)
                    if assigned:
                        self.schedule.append(Stop(parcel.origin, parcel.state, parcel))

    def start_delivery(self):
        """"
        Starts the delivery of the scheduled parcel pick-ups and deliveries.
        """
        if not self.schedule:
            print(f"[t={self.sim.current_time}] {self.agent_id}: All deliveries complete!")

        else:
            # Next stop is just first in schedule
            next_stop = self.schedule[0]

            # Calculate travel time between current position and next stop location
            distance = abs(next_stop.location - self.position)
            travel_time = distance / self.speed

            print(f"[t={self.sim.current_time}] {self.agent_id}: Traveling from {self.position} to {next_stop.location} (will take {travel_time:.1f}s)")
            self.schedule_action(travel_time, self.arrive_at_stop, next_stop)

    def arrive_at_stop(self, stop):
        """"
        Courier arrives at a Stop and parcel is picked up or delivered.
        """
        # Update the courier's position
        self.position = stop.location
        print(f"[t={self.sim.current_time}] {self.agent_id}: Arrived at {self.position}")

        # Remove from schedule
        #self.schedule.remove(stop)
        self.schedule.pop(0)

        # Deliver or pickup
        stop_type = stop.type
        if stop_type == "waiting_pick_up":
            pick_up_parcel = stop.parcel
            print(f"[t={self.sim.current_time}] {self.agent_id}: Picked up parcel at {stop.location}")
            self.carried_parcels.append(pick_up_parcel)
            pick_up_parcel.state = "being_delivered"
            self.schedule.append(Stop(pick_up_parcel.destination, pick_up_parcel.state, pick_up_parcel))
        elif stop_type == "being_delivered":
            drop_off_parcel = stop.parcel
            print(f"[t={self.sim.current_time}] {self.agent_id}: Delivered parcel at {stop.location}")
            self.carried_parcels.remove(drop_off_parcel)

        # Continue to next destination
        self.start_delivery()


class Parcel:
    """
    A parcel that can be delivered.
    """

    def __init__(self, contents: str, origin: int, destination: int, weight: float, fare: float):
        self.contents: str = contents
        self.origin: int = origin
        self.destination: int = destination
        self.weight: float = weight
        self.fare: float = fare
        self.id: Optional[str] = None
        self.state: str = "waiting_pick_up"

    def __repr__(self):
        return (
            f"Parcel(id={self.id}, contents={self.contents}, origin={self.origin}, destination={self.destination}, weight={self.weight}, "
            f"fare={self.fare}, state={self.state})"
        )


if __name__ == "__main__":
    sim = SimulationKernel()

    # Create agents
    uber = Platform("uber")
    customer_sending = Customer("customer_sending", 10)
    customer_receiving = Customer("customer_receiving", 210)
    courier = Courier("courier", 0, 20, 30)

    sim.register_agent(uber)
    sim.register_agent(customer_sending)
    sim.register_agent(customer_receiving)
    sim.register_agent(courier)

    # Define already existing to-be-delivered parcels in the platform
    sample_parcel_1 = Parcel("socks", 100, 210, 0.5, 10)
    sample_parcel_2 = Parcel("books", 100, 210, 4, 10)
    sim.schedule(1.0, lambda _: uber.initialize_deliveries(
        parcels=[sample_parcel_1, sample_parcel_2],
    ), None)

    sim.schedule(5.0, lambda _: customer_sending.request_delivery(
        Parcel("laptop", 10, 100, 5, 10),
        uber
    ), None)

    sim.schedule(10.0, lambda _: courier.ask_for_parcels(uber), None)

    sim.schedule(15.0, lambda _: courier.start_delivery(), None)

    print("Starting simulation...\n")
    sim.run(until=100.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")