from typing import List

from parcel_delivery.entities.courier import Courier
from parcel_delivery.entities.auction import Auction
from parcel_delivery.core.message import Message
from parcel_delivery.core.agent import Agent


class Platform(Agent):
    """
    Agent that generates auctions for parcel delivery.
    It receives customers' parcel delivery requests and assigns them to couriers.
    """

    def __init__(self, entity_id: str):
        super().__init__(entity_id)
        self.auction_count: int = 0
        self.auctions: List["Auction"] = []
        self.subscribed_couriers: List["Courier"] = []

    def register_courier(self, courier: "Courier"):
        """"
        Adds a courier to the platform's current courier subscribers.
        """
        self.subscribed_couriers.append(courier)

    def receive_message(self, message: "Message"):
        """
        Handle incoming message. Platform can receive
            - DELIVERY_REQUEST message from Customer
            - COMPLETE_DELIVERY_NOTIFICATION message from Courier

        Args:
            message: The incoming message
        """
        if message.msg_type == "DELIVERY_REQUEST":
            self.handle_delivery_request(message)
        elif message.msg_type == "COMPLETE_DELIVERY_NOTIFICATION":
            self.handle_complete_delivery_notification(message)

    def handle_delivery_request(self, message: "Message"):
        """
        A new auction with the parcel delivery request is created and started, and the couriers are notified.

        Args:
            message: The message containing the parcel to be delivered
        """
        # Create the new auction
        auction_name = "auction" + str(self.auction_count)
        parcel = message.content["parcel"]
        new_auction = Auction(auction_name, parcel)
        self.auctions.append(new_auction)
        self.auction_count += 1
        self.sim.register_entity(new_auction)

        # Start the new auction
        self.log_event_message(f"A new auction for {parcel.contents} has started")
        self.schedule_action(delay=0.0, action=new_auction.start_bidding)
        self.schedule_action(delay=0.0, action=self.send_auction_notification, data={"auction": new_auction})

    def handle_complete_delivery_notification(self, message: "Message"):
        """
        The customer is notified about the delivery of the parcel.

        Args:
            message: The message
        """
        raise NotImplementedError

    def send_auction_notification(self, auction: "Auction"):
        """
        Notifies the subscribed couriers of a new auction for a parcel.

        Args:
            auction: The auction to be notified of
        """

        self.log_event_message(f"Sent AUCTION_NOTIFICATION for {auction.auctioned_parcel.contents} to all subscribed couriers")
        for courier in self.subscribed_couriers:
            self.send_message(receiver_id=courier.entity_id,
                              msg_type="AUCTION_NOTIFICATION",
                              content={"auction": auction},
                              delay=0.0)
