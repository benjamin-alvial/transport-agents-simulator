import random
from typing import List

from parcel_delivery.agents.auction import Auction
from parcel_delivery.simulation.message import Message
from parcel_delivery.agents.agent import Agent
from parcel_delivery.models.bid import Bid
from parcel_delivery.models.stop import Stop
from parcel_delivery.models.parcel import Parcel

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

    def receive_message(self, message: "Message"):
        """
        Handle incoming message. Courier can receive: AUCTION_NOTIFICATION message from Platform or
        WINNER_NOTIFICATION message from Platform.

        Args:
            message: The incoming message
        """
        if message.msg_type == "AUCTION_NOTIFICATION":
            self.handle_auction_notification(message)
        elif message.msg_type == "WINNER_NOTIFICATION":
            self.handle_winner_notification(message)
        elif message.msg_type == "LOSER_NOTIFICATION":
            self.handle_loser_notification()

    def handle_auction_notification(self, message: "Message"):
        """"
        Receives a notification that a new auction for a parcel has started.
        """
        auction = message.content["auction"]
        parcel = auction.auctioned_parcel

        # Courier first sees if the auctioned parcel fits its capacity
        if self.current_load + parcel.weight <= self.capacity:
            BID_VALUE = random.randint(1, 100)
            bid = Bid(self, auction, BID_VALUE)

            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Generates bid of {BID_VALUE} to add {parcel.contents} parcel to vehicle")
            self.schedule_action(delay=5.0, action=self.send_bid_request, data=(bid,auction))

    def handle_winner_notification(self, message: "Message"):
        """ Prints happy message and adds parcel to schedule and vehicle."""
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Won the auction.")
        parcel = message.content["parcel"]
        self.schedule.append(Stop(parcel.origin, parcel.state, parcel))
        self.schedule_action(delay=0.0, action=self.start_delivery, data=None)

    def handle_loser_notification(self):
        """ Prints sad message."""
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Lost the auction.")

    def send_bid_request(self, bid: "Bid", auction: "Auction"):
        """
        Sends a bis request to an Auction.

        Args:
            bid: The bid to send
            auction: The auction to be bid on
        """
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Sent BID_REQUEST for {auction.auctioned_parcel.contents} for value {bid.value}")
        self.send_message(receiver_id=auction.agent_id,
                          msg_type="BID_REQUEST",
                          content={"bid": bid},
                          delay=0.0)

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
        self.schedule.pop(0)

        # Deliver or pickup
        stop_type = stop.stop_type
        if stop_type == "WAITING_PICK_UP":
            pick_up_parcel = stop.parcel
            print(f"[t={self.sim.current_time}] {self.agent_id}: Picked up parcel at {stop.location}")
            self.carried_parcels.append(pick_up_parcel)
            pick_up_parcel.state = "BEING_DELIVERED"
            self.schedule.append(Stop(pick_up_parcel.destination, pick_up_parcel.state, pick_up_parcel))
        elif stop_type == "BEING_DELIVERED":
            drop_off_parcel = stop.parcel
            print(f"[t={self.sim.current_time}] {self.agent_id}: Delivered parcel at {stop.location}")
            self.carried_parcels.remove(drop_off_parcel)
            drop_off_parcel.state = "DELIVERED"

        # Continue to next destination
        self.start_delivery()