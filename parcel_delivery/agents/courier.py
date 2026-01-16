from typing import List, TYPE_CHECKING

from parcel_delivery.agents.agent import Agent
from parcel_delivery.models.stop import Stop
from parcel_delivery.models.parcel import Parcel

if TYPE_CHECKING:
    from parcel_delivery.agents.platform import Platform


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