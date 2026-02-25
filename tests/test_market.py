import pytest
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.market.vehicle import Vehicle
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.market.market import Market, ExcessDemandError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_requests(n: int, weight: float = 10, destination: int = 1):
    return [DeliveryRequest(f"parcel_{i}", weight=weight, destination=destination)
            for i in range(n)]

def make_courier(courier_id: str, vehicle_type: str, capacity: int, n_vehicles: int):
    vehicles = [Vehicle(vehicle_type=vehicle_type, travel_time_factor=1, capacity=capacity)
                for _ in range(n_vehicles)]
    return Courier(courier_id, vehicles=vehicles)


# ---------------------------------------------------------------------------
# DeliveryRequest
# ---------------------------------------------------------------------------

class TestDeliveryRequest:
    def test_attributes(self):
        r = DeliveryRequest("p1", weight=15.0, destination=5)
        assert r.name == "p1"
        assert r.weight == 15.0
        assert r.destination == 5


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------

class TestVehicle:
    def test_attributes(self):
        v = Vehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100)
        assert v.vehicle_type == "car"
        assert v.travel_time_factor == 1.0
        assert v.capacity == 100


# ---------------------------------------------------------------------------
# Courier
# ---------------------------------------------------------------------------

class TestCourier:
    def test_initial_state(self):
        c = make_courier("c1", "car", capacity=100, n_vehicles=3)
        assert c.courier_id == "c1"
        assert c.assigned_delivery_requests == []

    def test_total_capacity(self):
        c = make_courier("c1", "car", capacity=100, n_vehicles=3)
        assert c.total_capacity() == 300

    def test_remaining_capacity_empty(self):
        c = make_courier("c1", "car", capacity=100, n_vehicles=3)
        assert c.remaining_capacity() == 300

    def test_remaining_capacity_after_assignment(self):
        c = make_courier("c1", "car", capacity=100, n_vehicles=3)
        c.assigned_delivery_requests.append(DeliveryRequest("p1", weight=50, destination=1))
        assert c.remaining_capacity() == 250


# ---------------------------------------------------------------------------
# Market — full_example scenario
# ---------------------------------------------------------------------------

class TestMarketFullExample:
    """Reproduces the scenario from full_example.py."""

    def setup_method(self):
        self.requests = make_requests(40, weight=10)
        self.courier_1 = make_courier("courier_1", "car", capacity=100, n_vehicles=3)   # total 300
        self.courier_2 = make_courier("courier_2", "bike", capacity=20, n_vehicles=5)   # total 100
        self.market = Market()

    def test_all_requests_assigned(self):
        self.market.assign_delivery_requests(
            self.requests, [self.courier_1, self.courier_2])
        total = (len(self.courier_1.assigned_delivery_requests)
                 + len(self.courier_2.assigned_delivery_requests))
        assert total == 40

    def test_distribution_matches_capacity_ratio(self):
        self.market.assign_delivery_requests(
            self.requests, [self.courier_1, self.courier_2])
        assert len(self.courier_1.assigned_delivery_requests) == 30
        assert len(self.courier_2.assigned_delivery_requests) == 10

    def test_no_courier_exceeds_capacity(self):
        self.market.assign_delivery_requests(
            self.requests, [self.courier_1, self.courier_2])
        assert self.courier_1.remaining_capacity() >= 0
        assert self.courier_2.remaining_capacity() >= 0


# ---------------------------------------------------------------------------
# Market — edge cases
# ---------------------------------------------------------------------------

class TestMarketEdgeCases:
    def test_single_courier_gets_all(self):
        courier = make_courier("c1", "car", capacity=1000, n_vehicles=1)
        requests = make_requests(10, weight=10)
        Market().assign_delivery_requests(requests, [courier])
        assert len(courier.assigned_delivery_requests) == 10

    def test_requests_exceed_total_capacity_raises(self):
        courier = make_courier("c1", "car", capacity=50, n_vehicles=1)
        requests = make_requests(10, weight=10)  # total weight 100 > capacity 50
        with pytest.raises(ExcessDemandError):
            Market().assign_delivery_requests(requests, [courier])

    def test_empty_requests(self):
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1)
        Market().assign_delivery_requests([], [courier])
        assert courier.assigned_delivery_requests == []

    def test_round_robin_order(self):
        """First request goes to courier_1, second to courier_2, and so on."""
        c1 = make_courier("c1", "car", capacity=100, n_vehicles=1)
        c2 = make_courier("c2", "car", capacity=100, n_vehicles=1)
        requests = make_requests(4, weight=10)
        Market().assign_delivery_requests(requests, [c1, c2])
        assert requests[0] in c1.assigned_delivery_requests
        assert requests[1] in c2.assigned_delivery_requests
        assert requests[2] in c1.assigned_delivery_requests
        assert requests[3] in c2.assigned_delivery_requests

    def test_full_courier_is_skipped(self):
        """When courier_1 is full, requests overflow to courier_2."""
        c1 = make_courier("c1", "car", capacity=10, n_vehicles=1)   # fits 1 request
        c2 = make_courier("c2", "car", capacity=100, n_vehicles=1)
        requests = make_requests(3, weight=10)
        Market().assign_delivery_requests(requests, [c1, c2])
        assert len(c1.assigned_delivery_requests) == 1
        assert len(c2.assigned_delivery_requests) == 2

    def test_unknown_strategy_raises(self):
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1)
        with pytest.raises(ValueError, match="Unknown strategy"):
            Market().assign_delivery_requests([], [courier], strategy="UNKNOWN")
