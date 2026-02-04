import random
from typing import List, Optional

from parcel_delivery.entities.auction import Auction
from parcel_delivery.core.message import Message
from parcel_delivery.core.agent import Agent
from parcel_delivery.models.bid import Bid
from parcel_delivery.models.stop import Stop
from parcel_delivery.models.parcel import Parcel

class Courier(Agent):
    """
    Agent that delivers Parcels.
    """

    def __init__(self, entity_id: str, start_node: int, capacity: int, speed: float):
        super().__init__(entity_id)
        self.current_node: Optional[int] = start_node
        self.target_node: Optional[int] = None
        self.capacity: int = capacity
        self.speed: float = speed
        self.itinerary: List[Stop] = []
        self.current_load: float = 0
        self.carried_parcels: List[Parcel] = []

    def receive_message(self, message: "Message"):
        """
        Handle incoming message.
        Courier can receive:
            AUCTION_NOTIFICATION message from Platform or
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
        print(f"[t={self.sim.current_time:.1f}] {self.entity_id}: Received auction notification.")
        auction = message.content["auction"]
        parcel = auction.auctioned_parcel

        # Courier first sees if the auctioned parcel fits its capacity
        if self.current_load + parcel.weight <= self.capacity:
            BID_VALUE = random.randint(1, 10)
            bid = Bid(self, auction, BID_VALUE)

            print(f"[t={self.sim.current_time:.1f}] {self.entity_id}: Generates bid of {BID_VALUE} to add {parcel.contents} parcel to vehicle")
            self.schedule_action(delay=5.0, action=self.send_bid_request, data={"bid": bid, "auction": auction})

    def handle_winner_notification(self, message: "Message"):
        """ Prints happy message and adds parcel to itinerary and vehicle."""
        print(f"[t={self.sim.current_time:.1f}] {self.entity_id}: Won the auction.")
        parcel = message.content["parcel"]
        self.itinerary.append(Stop(parcel.origin_node_id, parcel.state, parcel))
        self.schedule_action(delay=0.0, action=self.start_delivery)

    def handle_loser_notification(self):
        """ Prints sad message."""
        print(f"[t={self.sim.current_time:.1f}] {self.entity_id}: Lost the auction.")

    def send_bid_request(self, bid: "Bid", auction: "Auction"):
        """
        Sends a bid request to an Auction.

        Args:
            bid: The bid to send
            auction: The auction to be bid on
        """
        print(f"[t={self.sim.current_time:.1f}] {self.entity_id}: Sent BID_REQUEST for {auction.auctioned_parcel.contents} for value {bid.value}")
        self.send_message(receiver_id=auction.entity_id,
                          msg_type="BID_REQUEST",
                          content={"bid": bid},
                          delay=0.0)

    def start_delivery(self):
        """"
        Starts the delivery of the scheduled parcel pick-ups and deliveries.
        """
        if not self.itinerary:
            print(f"[t={self.sim.current_time}] {self.entity_id}: All deliveries complete!")

        else:
            # Next stop is just first in itinerary
            next_stop = self.itinerary[0]

            # Calculate the path of nodes that must be traveled to reach the destination stop.
            path = self.sim.network.shortest_path(self.current_node, next_stop.location_node_id)
            path_nodes = path[0]
            path_edges = path[1]
            distance = path[2]

            # Calculate travel time between current position and next stop location
            travel_time = distance / self.speed

            # Assign flows
            self.sim.network.add_flows(path_nodes, 1)

            # Starts traveling
            print(f"[t={self.sim.current_time}] {self.entity_id}: Traveling {self.current_node}->{next_stop.location_node_id} with the sequence {path_nodes} and edges {path_edges} (will take {travel_time:.1f}s)")
            self.current_node = None
            self.target_node = next_stop.location_node_id
            self.schedule_action(travel_time, self.arrive_at_stop, {"stop": next_stop})

    def arrive_at_stop(self, stop: "Stop"):
        """"
        Courier arrives at a Stop and parcel is picked up or delivered.
        """
        # Update the courier's position
        self.current_node = stop.location_node_id
        print(f"[t={self.sim.current_time}] {self.entity_id}: Arrived at {self.target_node}")
        self.target_node = None


        # Remove from itinerary
        self.itinerary.pop(0)

        # Deliver or pickup
        stop_type = stop.stop_type
        if stop_type == "WAITING_PICK_UP":
            pick_up_parcel = stop.parcel
            print(f"[t={self.sim.current_time}] {self.entity_id}: Picked up parcel at {stop.location_node_id}")
            self.carried_parcels.append(pick_up_parcel)
            pick_up_parcel.state = "BEING_DELIVERED"
            self.itinerary.append(Stop(pick_up_parcel.destination_node_id, pick_up_parcel.state, pick_up_parcel))
        elif stop_type == "BEING_DELIVERED":
            drop_off_parcel = stop.parcel
            print(f"[t={self.sim.current_time}] {self.entity_id}: Delivered parcel at {stop.location_node_id}")
            self.carried_parcels.remove(drop_off_parcel)
            drop_off_parcel.state = "DELIVERED"

        # Continue to next destination
        self.start_delivery()