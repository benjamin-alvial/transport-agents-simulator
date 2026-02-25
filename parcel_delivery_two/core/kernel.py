from typing import Callable
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.market.courier import Courier


class Kernel:
    def __init__(self):
        self.current_time: float = 0.0

    def initialize_loggers(self):
        pass

    def set_network(self, network: Network):
        pass

    def register_courier(self, courier: Courier):
        pass

    def register_entity(self, entity):
        pass

    def schedule(self, delay: float, action: Callable):
        pass

    def run(self, until: float):
        pass
