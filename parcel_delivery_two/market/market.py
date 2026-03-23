import logging
from typing import List, Tuple
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.market.courier import Courier

logger = logging.getLogger(__name__)


class Market:
    """Assigns delivery requests to couriers using a configurable strategy."""

    def assign_delivery_requests(
        self,
        delivery_requests: List[DeliveryRequest],
        couriers: List[Courier],
        strategy: str = "DEFAULT",
    ) -> Tuple[int, int]:
        """Assign a list of delivery requests to couriers.

        Modifies each courier's `assigned_delivery_requests` in place.
        Failed assignments are logged as warnings instead of raising errors.

        Args:
            delivery_requests: Ordered list of requests to assign.
            couriers: Available couriers.
            strategy: Assignment algorithm. Supported values: "DEFAULT".

        Returns:
            Tuple of (assigned_count, failed_count).

        Raises:
            ValueError: If an unsupported strategy is requested.
        """
        if strategy == "DEFAULT":
            return self._assign_round_robin(delivery_requests, couriers)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _assign_round_robin(
        self, delivery_requests: List[DeliveryRequest], couriers: List[Courier]
    ) -> Tuple[int, int]:
        """Assign requests in order, cycling through couriers one by one.

        For each request the algorithm tries couriers starting from where the
        previous assignment left off. A request can only be assigned to a courier
        whose location matches the request's origin. The first courier meeting
        both location and capacity requirements receives the request. The index
        then advances past that courier so the next request starts from the
        following one, producing a fair round-robin distribution bounded by
        each courier's total capacity.

        Failed assignments are logged as warnings instead of raising errors.

        Args:
            delivery_requests: Ordered list of requests to assign.
            couriers: Available couriers.

        Returns:
            Tuple of (assigned_count, failed_count).
        """
        n = len(couriers)
        index = 0
        assigned_count = 0
        failed_count = 0

        for request in delivery_requests:
            matching_couriers = [c for c in couriers if c.location == request.origin]
            if not matching_couriers:
                logger.warning(
                    f"No courier located at origin node {request.origin} for '{request.name}'"
                )
                failed_count += 1
                continue

            assigned = False
            for attempt in range(n):
                courier = couriers[(index + attempt) % n]
                if courier.location == request.origin:
                    if courier.remaining_capacity() >= request.weight:
                        courier.assigned_delivery_requests.append(request)
                        index = (index + attempt + 1) % n
                        assigned_count += 1
                        assigned = True
                        break

            if not assigned:
                logger.warning(
                    f"No courier at origin {request.origin} has capacity for "
                    f"'{request.name}' (weight={request.weight})"
                )
                failed_count += 1

        return assigned_count, failed_count
