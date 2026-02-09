import random
from typing import List, Optional

from parcel_delivery.environment.edge import Edge
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

    def __init__(self, entity_id: str, start_node: int, capacity: int):
        super().__init__(entity_id)
        self.current_node: Optional[int] = start_node # Last node that was visited
        self.next_node: Optional[int] = None # Next node to visit
        self.remaining_nodes: List[int] = [] # List of nodes to visit for a specific delivery
        self.next_stop: Optional[Stop] = None # Next stop to visit
        self.current_edge: Optional[Edge] = None

        self.capacity: int = capacity

        self.itinerary: List[Stop] = []
        self.current_load: float = 0
        self.carried_parcels: List[Parcel] = []

        self.vehicle_type: str = "courier"

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
        self.log_event_message(f"Received auction notification.")
        auction = message.content["auction"]
        parcel = auction.auctioned_parcel

        # Courier first sees if the auctioned parcel fits its capacity
        if self.current_load + parcel.weight <= self.capacity:
            BID_VALUE = random.randint(1, 10)
            bid = Bid(self, auction, BID_VALUE)

            self.log_event_message(f"Generates bid of {BID_VALUE} to add {parcel.contents} parcel to vehicle")
            self.schedule_action(delay=300.0, action=self.send_bid_request, data={"bid": bid, "auction": auction})

    def handle_winner_notification(self, message: "Message"):
        """ Prints happy message and adds parcel to itinerary and vehicle."""
        self.log_event_message(f"Won the auction.")
        parcel = message.content["parcel"]
        self.itinerary.append(Stop(parcel.origin_node_id, "PICKUP", parcel))
        self.carried_parcels.append(parcel)
        self.schedule_action(delay=0.0, action=self.start_journey)

    def handle_loser_notification(self):
        """ Prints sad message."""
        self.log_event_message(f"Lost the auction.")

    def send_bid_request(self, bid: "Bid", auction: "Auction"):
        """
        Sends a bid request to an Auction.

        Args:
            bid: The bid to send
            auction: The auction to be bid on
        """
        self.log_event_message(f"Sent BID_REQUEST for {auction.auctioned_parcel.contents} for value {bid.value}")
        self.send_message(receiver_id=auction.entity_id,
                          msg_type="BID_REQUEST",
                          content={"bid": bid},
                          delay=0.0)

    def start_journey(self):
        """"
        Starts the journey of the courier to complete a pickup or drop-off in its itinerary.
        """
        # Already traveling
        if self.remaining_nodes:
            return

        # No stops left
        if not self.itinerary:
            self.log_event_message(f"All deliveries complete!")
            return

        # Next stop is just first in itinerary
        self.next_stop = self.itinerary[0]

        # Calculate the shortest path of nodes to travel to the next stop
        path_nodes, path_edges, distance = self.sim.network.shortest_path(
            self.current_node,
            self.next_stop.location_node_id)

        # Normalize path: remove current node if present
        if path_nodes and path_nodes[0] == self.current_node:
            path_nodes = path_nodes[1:]
        self.remaining_nodes = path_nodes

        # If already at stop node
        if not self.remaining_nodes:
            self.log_event_message(f"Already at stop {self.current_node}")
            self.handle_stop()
            return

        # Start movement
        self.log_event_message(f"Traveling from {self.current_node} to {self.next_stop.location_node_id} with the sequence {path_nodes} and edges {path_edges}")
        self.start_travel_to_next_node()

    def start_travel_to_next_node(self):
        """"
        Start traveling to the next node in remaining_nodes.
        """
        if not self.remaining_nodes:
            return

        # Next node is just first in the remaining_nodes
        self.next_node = self.remaining_nodes[0]

        # Calculate travel time between current position and next node
        edge = self.sim.network.get_edge(self.current_node, self.next_node)
        if edge is None:
            raise RuntimeError(
                f"No edge between {self.current_node} and {self.next_node}"
            )
        travel_time = edge.get_travel_time()

        # Starts traveling
        self.log_event_message(f"Traveling through edge {edge}, will arrive in {travel_time:.5f}s")
        self.current_edge = edge
        self.current_edge.vehicle_enters(self, self.sim.current_time)
        self.schedule_action(travel_time, self.arrive_at_node)

    def arrive_at_node(self):
        """"
        Courier arrives at a node.
        """
        # Exits edge
        self.current_edge.vehicle_exits(self, self.sim.current_time)
        self.current_edge = None

        # Update the courier's position
        self.log_event_message(f"Arrived at {self.next_node}")
        self.current_node = self.next_node
        self.next_node = None

        # Remove from remaining nodes to visit
        self.remaining_nodes.pop(0)

        # Check if this node is a stop
        if self.next_stop and self.current_node == self.next_stop.location_node_id:
            self.handle_stop()
        else:
            self.start_travel_to_next_node()

    def handle_stop(self):
        """"
        Handle pickup or drop-off at a stop.
        """
        stop = self.next_stop
        self.log_event_message(f"Handling stop at node {self.current_node}")

        # Deliver or pickup
        if stop.stop_type == "PICKUP":
            parcel = stop.parcel
            self.log_event_message(f"Picked up parcel at {self.current_node}")
            self.carried_parcels.append(parcel)
            parcel.state = "BEING_DELIVERED"
            self.itinerary.append(Stop(parcel.destination_node_id, "DROP_OFF", parcel))
        elif stop.stop_type == "DROP_OFF":
            parcel = stop.parcel
            self.log_event_message(f"Delivered parcel at {self.current_node}")
            self.carried_parcels.remove(parcel)
            parcel.state = "DELIVERED"

        # Remove completed stop
        self.itinerary.pop(0)
        self.next_stop = None
        self.remaining_nodes = []

        # Continue with next stop
        self.start_journey()
