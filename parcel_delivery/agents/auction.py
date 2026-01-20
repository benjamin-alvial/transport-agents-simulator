from typing import List, TYPE_CHECKING

from parcel_delivery.simulation.message import Message
from parcel_delivery.agents.agent import Agent

if TYPE_CHECKING:
    from parcel_delivery.agents.courier import Courier
    from parcel_delivery.models.bid import Bid
    from parcel_delivery.models.parcel import Parcel


class Auction(Agent):
    """
    Represents a Platform's Auction for a Parcel's delivery.
    It is created when a Customer requests the delivery of a Parcel.
    """

    def __init__(self, agent_id: str, auctioned_parcel: "Parcel"):
        super().__init__(agent_id)
        self.auctioned_parcel: "Parcel" = auctioned_parcel
        self.starting_price: float = auctioned_parcel.fare
        self.duration: float = 20
        self.bids: List["Bid"] = []

    def start_bidding(self):
        """Begins bidding for the auctioned parcel."""
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Bidding for {self.auctioned_parcel.contents} has started. Starting price: {self.starting_price}. Duration: {self.duration}")
        self.schedule_action(self.duration, self.end_bidding)

    def receive_message(self, message: "Message"):
        """
        Handle incoming message. Auction can receive: BID_REQUEST from Courier.

        Args:
            message: The incoming message
        """
        if message.msg_type == "BID_REQUEST":
            self.handle_bid_request(message)

    def handle_bid_request(self, message: "Message"):
        """
        Adds the bid to the current bids.

        Args:
            message: The message containing the bid to be added
        """
        bid = message.content["bid"]
        if bid.value <= self.starting_price:
            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Bid by {bid.courier.agent_id} for value {bid.value} submitted.")
            self.bids.append(bid)
        else:
            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Bid by {bid.courier.agent_id} for value {bid.value} too high, not accepted.")

    def end_bidding(self):
        """Ends bidding for the auctioned parcel."""
        print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Bidding has ended.")
        winner = self.determine_winner()
        for bid in self.bids:
            courier = bid.courier
            if courier == winner:
                self.send_winner_notification(courier)
            else:
                self.send_loser_notification(courier)

    def determine_winner(self) -> "Courier":
        """
        Determines the winner of the auction by choosing the Courier whose Bid has the lowest price.
        """
        min_bid = min(self.bids, key=lambda bid: bid.value)
        winning_courier = min_bid.courier
        return winning_courier

    def send_winner_notification(self, courier: "Courier"):
        """
        Sends notification to the courier that won the auction.

        Args:
            courier: The courier that has won the auction
        """
        self.send_message(receiver_id=courier.agent_id,
                          msg_type="WINNER_NOTIFICATION",
                          content={"parcel": self.auctioned_parcel},
                          delay=0.0)

    def send_loser_notification(self, courier: "Courier"):
        """
        Sends notification to a courier that lost the auction.

        Args:
            courier: A courier that has lost the auction
        """
        self.send_message(receiver_id=courier.agent_id,
                          msg_type="LOSER_NOTIFICATION",
                          content=None,
                          delay=0.0)