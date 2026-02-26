from typing import List, TYPE_CHECKING
from parcel_delivery_two.market.vehicle import Vehicle

if TYPE_CHECKING:
    from parcel_delivery_two.market.delivery_request import DeliveryRequest


class Courier:
    """A delivery courier that owns a fleet of vehicles.

    After market assignment, `assigned_delivery_requests` holds the requests
    this courier is responsible for delivering.

    Attributes:
        courier_id: Unique identifier for the courier.
        vehicles: Fleet of vehicles available to this courier.
        location: Node ID where all vehicles start (depot).
        assigned_delivery_requests: Requests assigned by the market.
    """

    def __init__(self, courier_id: str, vehicles: List[Vehicle], location: int):
        self.courier_id = courier_id
        self.vehicles = vehicles
        self.location = location
        self.assigned_delivery_requests: List["DeliveryRequest"] = []

    def total_capacity(self) -> float:
        """Sum of the capacities of all vehicles in the fleet."""
        return sum(v.capacity for v in self.vehicles)

    def remaining_capacity(self) -> float:
        """Remaining capacity after accounting for already-assigned request weights."""
        assigned_weight = sum(r.weight for r in self.assigned_delivery_requests)
        return self.total_capacity() - assigned_weight
