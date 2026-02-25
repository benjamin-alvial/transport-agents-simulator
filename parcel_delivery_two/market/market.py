from typing import List
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.market.courier import Courier


class ExcessDemandError(Exception):
    """Raised when a delivery request cannot be assigned to any courier."""


class Market:
    """Assigns delivery requests to couriers using a configurable strategy."""

    def assign_delivery_requests(self, delivery_requests: List[DeliveryRequest],
                                  couriers: List[Courier], strategy: str = "DEFAULT"):
        """Assign a list of delivery requests to couriers.

        Modifies each courier's `assigned_delivery_requests` in place.

        Args:
            delivery_requests: Ordered list of requests to assign.
            couriers: Available couriers.
            strategy: Assignment algorithm. Supported values: "DEFAULT".

        Raises:
            ValueError: If an unsupported strategy is requested.
            ExcessDemandError: If any request cannot be assigned (all couriers full).
        """
        if strategy == "DEFAULT":
            self._assign_round_robin(delivery_requests, couriers)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _assign_round_robin(self, delivery_requests: List[DeliveryRequest],
                             couriers: List[Courier]):
        """Assign requests in order, cycling through couriers one by one.

        For each request the algorithm tries couriers starting from where the
        previous assignment left off. The first courier with enough remaining
        capacity receives the request. The index then advances past that courier
        so the next request starts from the following one, producing a fair
        round-robin distribution bounded by each courier's total capacity.

        Args:
            delivery_requests: Ordered list of requests to assign.
            couriers: Available couriers.
        """
        n = len(couriers)
        index = 0
        for request in delivery_requests:
            for attempt in range(n):
                courier = couriers[(index + attempt) % n]
                if courier.remaining_capacity() >= request.weight:
                    courier.assigned_delivery_requests.append(request)
                    index = (index + attempt + 1) % n
                    break
            else:
                raise ExcessDemandError(
                    f"No courier has capacity for '{request.name}' (weight={request.weight})"
                )
