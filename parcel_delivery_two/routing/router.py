from typing import List
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge


class Router:
    def __init__(self, courier: Courier, network: Network,
                 restrictions: List[ProhibitEdge], strategy: str = "DEFAULT"):
        self.courier = courier
        self.network = network
        self.restrictions = restrictions
        self.strategy = strategy

    def calculate_itinerary(self):
        pass
