import pytest
import logging
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.agents.courier_vehicle import CourierVehicle as Vehicle
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.market.market import Market, ExcessDemandError, LocationMismatchError
from parcel_delivery_two.market.depot import Depot


DEPOT = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_requests(n: int, weight: float = 10, origin: int = DEPOT, destination: int = 1):
    return [DeliveryRequest(f"parcel_{i}", weight=weight, origin=origin, destination=destination)
            for i in range(n)]

def make_courier(courier_id: str, vehicle_type: str, capacity: int, n_vehicles: int, location: int = DEPOT, vtt: float = 30.0/3600):
    vehicles = [Vehicle(vehicle_type=vehicle_type, travel_time_factor=1, capacity=capacity)
                for _ in range(n_vehicles)]
    return Courier(courier_id, vehicles=vehicles, location=location, vtt=vtt)


# ---------------------------------------------------------------------------
# DeliveryRequest
# ---------------------------------------------------------------------------

class TestDeliveryRequest:
    def test_attributes(self):
        r = DeliveryRequest("p1", weight=15.0, origin=2, destination=5)
        assert r.name == "p1"
        assert r.weight == 15.0
        assert r.origin == 2
        assert r.destination == 5

    def test_start_time_none_initially(self):
        r = DeliveryRequest("p1", weight=10.0, origin=1, destination=2)
        assert r.start_time is None

    def test_completion_time_none_initially(self):
        r = DeliveryRequest("p1", weight=10.0, origin=1, destination=2)
        assert r.completion_time is None

    def test_get_delivery_time_none_when_not_started(self):
        r = DeliveryRequest("p1", weight=10.0, origin=1, destination=2)
        assert r.get_delivery_time() is None

    def test_get_delivery_time_none_when_not_completed(self):
        r = DeliveryRequest("p1", weight=10.0, origin=1, destination=2)
        r.start_time = 100.0
        assert r.get_delivery_time() is None

    def test_get_delivery_time_calculates_correctly(self):
        r = DeliveryRequest("p1", weight=10.0, origin=1, destination=2)
        r.start_time = 100.0
        r.completion_time = 250.0
        assert r.get_delivery_time() == 150.0

    def test_get_delivery_time_zero_duration(self):
        r = DeliveryRequest("p1", weight=10.0, origin=1, destination=2)
        r.start_time = 100.0
        r.completion_time = 100.0
        assert r.get_delivery_time() == 0.0


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
        c.assigned_delivery_requests.append(DeliveryRequest("p1", weight=50, origin=2, destination=1))
        assert c.remaining_capacity() == 250

    def test_remaining_capacity_exactly_zero(self):
        c = make_courier("c1", "car", capacity=100, n_vehicles=1)
        c.assigned_delivery_requests.append(DeliveryRequest("p1", weight=100, origin=2, destination=1))
        assert c.remaining_capacity() == 0

    def test_remaining_capacity_negative_not_possible(self):
        """Market should prevent exceeding capacity, but test the math."""
        c = make_courier("c1", "car", capacity=100, n_vehicles=1)
        c.assigned_delivery_requests.append(DeliveryRequest("p1", weight=150, origin=2, destination=1))
        assert c.remaining_capacity() == -50

    def test_vtt_default(self):
        """Default VTT should be $30/hour = $0.00833/second."""
        c = make_courier("c1", "car", capacity=100, n_vehicles=1)
        expected_vtt = 30.0 / 3600
        assert c.vtt == expected_vtt

    def test_vtt_custom(self):
        """Courier can have custom VTT."""
        c = make_courier("c1", "car", capacity=100, n_vehicles=1, vtt=50.0/3600)
        assert c.vtt == 50.0 / 3600

    def test_multiple_vehicle_types(self):
        """Courier can have different vehicle types."""
        car = Vehicle("car", 1.0, 100)
        bike = Vehicle("bike", 0.5, 20)
        c = Courier("c1", vehicles=[car, bike], location=DEPOT)
        assert c.total_capacity() == 120


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

    def test_returns_tuple_counts(self):
        assigned, failed = self.market.assign_delivery_requests(
            self.requests, [self.courier_1, self.courier_2])
        assert assigned == 40
        assert failed == 0


# ---------------------------------------------------------------------------
# Market — edge cases
# ---------------------------------------------------------------------------

class TestMarketEdgeCases:
    def test_single_courier_gets_all(self):
        courier = make_courier("c1", "car", capacity=1000, n_vehicles=1)
        requests = make_requests(10, weight=10)
        Market().assign_delivery_requests(requests, [courier])
        assert len(courier.assigned_delivery_requests) == 10

    def test_requests_exceed_total_capacity_logs_warning(self):
        courier = make_courier("c1", "car", capacity=50, n_vehicles=1)
        requests = make_requests(10, weight=10)  # total weight 100 > capacity 50
        assigned, failed = Market().assign_delivery_requests(requests, [courier])
        assert assigned == 5  # Only 5 can be assigned with capacity 50
        assert failed == 5  # Remaining 5 fail

    def test_empty_requests(self):
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1)
        assigned, failed = Market().assign_delivery_requests([], [courier])
        assert courier.assigned_delivery_requests == []
        assert assigned == 0
        assert failed == 0

    def test_no_couriers(self):
        """Should handle empty courier list gracefully."""
        requests = make_requests(5, weight=10)
        assigned, failed = Market().assign_delivery_requests(requests, [])
        assert assigned == 0
        assert failed == 5

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

    def test_weighted_requests_different_weights(self):
        """Requests with different weights should be assigned correctly."""
        c1 = make_courier("c1", "car", capacity=100, n_vehicles=1)
        requests = [
            DeliveryRequest("p1", weight=30, origin=DEPOT, destination=1),
            DeliveryRequest("p2", weight=50, origin=DEPOT, destination=1),
            DeliveryRequest("p3", weight=20, origin=DEPOT, destination=1),
        ]
        assigned, failed = Market().assign_delivery_requests(requests, [c1])
        assert assigned == 3
        assert c1.remaining_capacity() == 0  # 30+50+20 = 100

    def test_heavy_request_exceeds_capacity(self):
        """Single heavy request that exceeds capacity should fail."""
        c1 = make_courier("c1", "car", capacity=50, n_vehicles=1)
        requests = [DeliveryRequest("p1", weight=100, origin=DEPOT, destination=1)]
        assigned, failed = Market().assign_delivery_requests(requests, [c1])
        assert assigned == 0
        assert failed == 1


# ---------------------------------------------------------------------------
# Market — location matching
# ---------------------------------------------------------------------------

class TestMarketLocationMatching:
    def test_location_mismatch_logs_warning(self):
        """Requests with different origins than courier location should fail."""
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1, location=2)
        requests = [DeliveryRequest("p1", weight=10, origin=5, destination=1)]
        assigned, failed = Market().assign_delivery_requests(requests, [courier])
        assert assigned == 0
        assert failed == 1

    def test_location_matches_assigns_successfully(self):
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1, location=2)
        requests = [DeliveryRequest("p1", weight=10, origin=2, destination=1)]
        Market().assign_delivery_requests(requests, [courier])
        assert len(courier.assigned_delivery_requests) == 1

    def test_multiple_couriers_different_locations(self):
        """Requests should only go to couriers at matching origin."""
        c1 = make_courier("c1", "car", capacity=100, n_vehicles=1, location=2)
        c2 = make_courier("c2", "car", capacity=100, n_vehicles=1, location=3)
        requests = [
            DeliveryRequest("p1", weight=10, origin=2, destination=1),
            DeliveryRequest("p2", weight=10, origin=3, destination=1),
        ]
        Market().assign_delivery_requests(requests, [c1, c2])
        assert len(c1.assigned_delivery_requests) == 1
        assert len(c2.assigned_delivery_requests) == 1

    def test_request_origin_not_in_network(self):
        """Request origin that no courier can serve should fail."""
        c1 = make_courier("c1", "car", capacity=100, n_vehicles=1, location=2)
        c2 = make_courier("c2", "car", capacity=100, n_vehicles=1, location=3)
        requests = [DeliveryRequest("p1", weight=10, origin=99, destination=1)]
        assigned, failed = Market().assign_delivery_requests(requests, [c1, c2])
        assert assigned == 0
        assert failed == 1

    def test_multiple_requests_same_origin(self):
        """Multiple requests from same origin distributed among couriers there."""
        c1 = make_courier("c1", "car", capacity=100, n_vehicles=1, location=2)
        c2 = make_courier("c2", "car", capacity=100, n_vehicles=1, location=2)
        requests = make_requests(4, weight=10, origin=2)
        Market().assign_delivery_requests(requests, [c1, c2])
        # Should be distributed round-robin
        assert len(c1.assigned_delivery_requests) == 2
        assert len(c2.assigned_delivery_requests) == 2


# ---------------------------------------------------------------------------
# Market — logging verification
# ---------------------------------------------------------------------------

class TestMarketLogging:
    def test_location_mismatch_logs_warning_message(self, caplog):
        """Verify that location mismatch logs appropriate warning."""
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1, location=2)
        requests = [DeliveryRequest("p1", weight=10, origin=5, destination=1)]
        
        with caplog.at_level(logging.WARNING):
            Market().assign_delivery_requests(requests, [courier])
        
        assert "No courier located at origin node 5" in caplog.text

    def test_excess_capacity_logs_warning_message(self, caplog):
        """Verify that excess demand logs appropriate warning."""
        courier = make_courier("c1", "car", capacity=50, n_vehicles=1)
        requests = [
            DeliveryRequest("p1", weight=30, origin=DEPOT, destination=1),
            DeliveryRequest("p2", weight=30, origin=DEPOT, destination=1),  # Exceeds capacity
        ]
        
        with caplog.at_level(logging.WARNING):
            Market().assign_delivery_requests(requests, [courier])
        
        assert "No courier at origin" in caplog.text
        assert "has capacity" in caplog.text


# ---------------------------------------------------------------------------
# Market — exception classes
# ---------------------------------------------------------------------------

class TestMarketExceptions:
    def test_excess_demand_error_exists(self):
        """ExcessDemandError exception class should exist."""
        assert ExcessDemandError is not None
        # These exceptions are defined but not raised in current implementation
        # (warnings are logged instead)

    def test_location_mismatch_error_exists(self):
        """LocationMismatchError exception class should exist."""
        assert LocationMismatchError is not None

    def test_exceptions_inherit_from_exception(self):
        """Custom exceptions should inherit from Exception."""
        assert issubclass(ExcessDemandError, Exception)
        assert issubclass(LocationMismatchError, Exception)


# ---------------------------------------------------------------------------
# Depot
# ---------------------------------------------------------------------------

class TestDepot:
    def test_depot_creation(self):
        """Depot should be created with depot_id and node_id."""
        depot = Depot(depot_id="depot_1", node_id=5)
        assert depot.depot_id == "depot_1"
        assert depot.node_id == 5

    def test_depot_different_nodes(self):
        """Multiple depots can be at different nodes."""
        depot_a = Depot(depot_id="depot_a", node_id=2)
        depot_b = Depot(depot_id="depot_b", node_id=10)
        assert depot_a.node_id != depot_b.node_id

    def test_depot_same_node_different_ids(self):
        """Multiple depots can share the same node with different IDs."""
        depot_1 = Depot(depot_id="main_depot", node_id=5)
        depot_2 = Depot(depot_id="secondary_depot", node_id=5)
        assert depot_1.node_id == depot_2.node_id
        assert depot_1.depot_id != depot_2.depot_id


# ---------------------------------------------------------------------------
# Multi-Depot Market Scenarios
# ---------------------------------------------------------------------------

class TestMultiDepotMarket:
    """Tests for multiple depots with various courier/request distributions."""

    def test_courier_at_depot_gets_requests_from_that_depot(self):
        """Couriers at depot A should only get requests from depot A."""
        depot_a = Depot(depot_id="depot_a", node_id=2)
        depot_b = Depot(depot_id="depot_b", node_id=10)
        
        # Courier at depot A
        courier_a = make_courier("c1", "car", capacity=100, n_vehicles=1, location=depot_a.node_id)
        
        # Requests from both depots
        requests_from_a = make_requests(3, weight=10, origin=depot_a.node_id)
        requests_from_b = make_requests(2, weight=10, origin=depot_b.node_id)
        all_requests = requests_from_a + requests_from_b
        
        assigned, failed = Market().assign_delivery_requests(all_requests, [courier_a])
        
        # Only requests from depot A should be assigned
        assert assigned == 3
        assert failed == 2  # Requests from depot B fail
        assert len(courier_a.assigned_delivery_requests) == 3
        
        # Verify all assigned requests are from depot A
        for req in courier_a.assigned_delivery_requests:
            assert req.origin == depot_a.node_id

    def test_couriers_at_different_depots_get_own_requests(self):
        """Couriers at different depots should get requests from their respective depots."""
        depot_a = Depot(depot_id="depot_a", node_id=2)
        depot_b = Depot(depot_id="depot_b", node_id=10)
        
        # Couriers at different depots
        courier_a = make_courier("c1", "car", capacity=100, n_vehicles=1, location=depot_a.node_id)
        courier_b = make_courier("c2", "bike", capacity=50, n_vehicles=1, location=depot_b.node_id)
        
        # Requests from both depots
        requests_from_a = make_requests(2, weight=10, origin=depot_a.node_id)
        requests_from_b = make_requests(2, weight=10, origin=depot_b.node_id)
        all_requests = requests_from_a + requests_from_b
        
        assigned, failed = Market().assign_delivery_requests(all_requests, [courier_a, courier_b])
        
        assert assigned == 4
        assert failed == 0
        assert len(courier_a.assigned_delivery_requests) == 2
        assert len(courier_b.assigned_delivery_requests) == 2

    def test_depot_without_couriers_logs_warning(self, caplog):
        """Requests from a depot with no couriers should log warning."""
        depot_with_courier = Depot(depot_id="depot_with", node_id=2)
        depot_without_courier = Depot(depot_id="depot_without", node_id=10)
        
        # Only courier at depot_with
        courier = make_courier("c1", "car", capacity=100, n_vehicles=1, location=depot_with_courier.node_id)
        
        # Requests from depot without courier
        requests = make_requests(3, weight=10, origin=depot_without_courier.node_id)
        
        with caplog.at_level(logging.WARNING):
            assigned, failed = Market().assign_delivery_requests(requests, [courier])
        
        assert assigned == 0
        assert failed == 3
        assert f"No courier located at origin node {depot_without_courier.node_id}" in caplog.text

    def test_mixed_assignment_with_depot_capacity(self):
        """Requests distributed across depots respecting capacity."""
        depot_a = Depot(depot_id="depot_a", node_id=2)
        depot_b = Depot(depot_id="depot_b", node_id=10)
        
        # Couriers at depot A only
        courier_a1 = make_courier("c1", "car", capacity=30, n_vehicles=1, location=depot_a.node_id)
        courier_a2 = make_courier("c2", "car", capacity=30, n_vehicles=1, location=depot_a.node_id)
        
        # Many requests from depot A, none from depot B
        requests_a = make_requests(8, weight=10, origin=depot_a.node_id)  # 80 total, but capacity is 60
        requests_b = make_requests(3, weight=10, origin=depot_b.node_id)  # No couriers at B
        all_requests = requests_a + requests_b
        
        assigned, failed = Market().assign_delivery_requests(all_requests, [courier_a1, courier_a2])
        
        assert assigned == 6  # 60 capacity at depot A
        assert failed == 5  # 2 from A (excess capacity) + 3 from B (no couriers)

    def test_round_robin_across_all_couriers(self):
        """Round-robin assignment cycles through all couriers, respecting location constraints."""
        depot_a = Depot(depot_id="depot_a", node_id=2)
        depot_b = Depot(depot_id="depot_b", node_id=10)
        
        # Multiple couriers at depot A, one at depot B
        courier_a1 = make_courier("c1", "car", capacity=100, n_vehicles=1, location=depot_a.node_id)
        courier_a2 = make_courier("c2", "car", capacity=100, n_vehicles=1, location=depot_a.node_id)
        courier_b = make_courier("c3", "car", capacity=100, n_vehicles=1, location=depot_b.node_id)
        
        # Interleaved requests from both depots
        requests = [
            DeliveryRequest("p1", weight=10, origin=depot_a.node_id, destination=1),  # Goes to a1
            DeliveryRequest("p2", weight=10, origin=depot_b.node_id, destination=1),  # Goes to b
            DeliveryRequest("p3", weight=10, origin=depot_a.node_id, destination=1),  # Goes to a1 (after b)
            DeliveryRequest("p4", weight=10, origin=depot_b.node_id, destination=1),  # Goes to b (after a1)
        ]
        
        Market().assign_delivery_requests(requests, [courier_a1, courier_a2, courier_b])
        
        # Round-robin continues across the full courier list:
        # p1 -> a1 (first match at depot A)
        # p2 -> b (first match at depot B, advances from a2)
        # p3 -> a1 (back to a1, advances from b)
        # p4 -> b (advances from a1)
        assert len(courier_a1.assigned_delivery_requests) == 2  # p1, p3
        assert len(courier_a2.assigned_delivery_requests) == 0  # Never matched
        assert len(courier_b.assigned_delivery_requests) == 2   # p2, p4

    def test_three_depots_varied_courier_coverage(self):
        """Three depots: two with couriers, one without."""
        depot_a = Depot(depot_id="depot_a", node_id=2)
        depot_b = Depot(depot_id="depot_b", node_id=10)
        depot_c = Depot(depot_id="depot_c", node_id=20)  # No couriers here
        
        # Couriers at depot A and B
        courier_a = make_courier("c1", "car", capacity=50, n_vehicles=1, location=depot_a.node_id)
        courier_b = make_courier("c2", "car", capacity=50, n_vehicles=1, location=depot_b.node_id)
        
        # Requests from all three depots
        requests_a = make_requests(3, weight=10, origin=depot_a.node_id)
        requests_b = make_requests(3, weight=10, origin=depot_b.node_id)
        requests_c = make_requests(2, weight=10, origin=depot_c.node_id)
        all_requests = requests_a + requests_b + requests_c
        
        assigned, failed = Market().assign_delivery_requests(all_requests, [courier_a, courier_b])
        
        assert assigned == 6  # 3 from A + 3 from B
        assert failed == 2  # Both from C (no couriers)
        assert len(courier_a.assigned_delivery_requests) == 3
        assert len(courier_b.assigned_delivery_requests) == 3

    def test_depot_node_used_in_full_example_pattern(self):
        """Replicate full_example pattern using Depot class."""
        main_depot = Depot(depot_id="depot_main", node_id=2)
        
        # Create couriers at the depot
        cars = [Vehicle(vehicle_type="car", travel_time_factor=1, capacity=100) for _ in range(2)]
        courier = Courier("courier1", vehicles=cars, location=main_depot.node_id)
        
        # Create requests from the depot
        requests = [
            DeliveryRequest(f"parcel_{i}", weight=10, origin=main_depot.node_id, destination=3)
            for i in range(15)
        ]
        
        assigned, failed = Market().assign_delivery_requests(requests, [courier])
        
        assert assigned == 15
        assert failed == 0
        assert len(courier.assigned_delivery_requests) == 15
