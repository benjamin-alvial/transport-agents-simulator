from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parcel_delivery.agents.courier import Courier
    from parcel_delivery.agents.auction import Auction


class Bid:
    """Represents a Courier's Bid on an Auction"""

    def __init__(self, courier: "Courier", auction: "Auction", value: float):
        self.courier: "Courier" = courier
        self.auction: "Auction" = auction
        self.value: float = value