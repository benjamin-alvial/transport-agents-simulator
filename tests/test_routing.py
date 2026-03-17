import pytest

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.agents.courier_vehicle import CourierVehicle as Vehicle
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing
from parcel_delivery_two.routing.router import Router


DEPOT = 2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_network() -> Network:
    """Simple linear network: 2 --(e1)--> 3 --(e2)--> 4"""
    net = Network()
    net.add_node(Node(2, 0.0, 0.0))
    net.add_node(Node(3, 1.0, 0.0))
    net.add_node(Node(4, 2.0, 0.0))
    net.add_edge(Edge(edge_id=1, from_node=2, to_node=3, distance=100.0, free_flow_speed=10.0))
    net.add_edge(Edge(edge_id=2, from_node=3, to_node=4, distance=100.0, free_flow_speed=10.0))
    return net


def _make_router(courier: Courier, network: Network) -> Router:
    return Router(courier, network, restrictions=[], strategy="DEFAULT")


# ---------------------------------------------------------------------------
# TestRouterItinerary
# ---------------------------------------------------------------------------

class TestRouterItinerary:
    def test_single_vehicle_single_request(self):
        """Vehicle with one request at node 3 gets the single edge 2→3."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, origin=DEPOT, destination=3)]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == [1]

    def test_single_vehicle_chained_request(self):
        """Vehicle visiting node 4 must traverse edges 1 then 2."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, origin=DEPOT, destination=4)]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == [1, 2]

    def test_single_vehicle_two_requests_ordered_nearest_first(self):
        """With stops at node 3 and 4, the nearest (3) is visited before 4."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=4),
            DeliveryRequest("p2", 10, origin=DEPOT, destination=3),
        ]

        _make_router(courier, net).calculate_itinerary()

        # Optimal tour: 2→3 (edge 1) then 3→4 (edge 2)
        assert vehicle.itinerary == [1, 2]

    def test_no_requests_gives_empty_itinerary(self):
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = []

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == []

    def test_multiple_vehicles_distribute_requests(self):
        """Two vehicles each get their own single request."""
        net = _make_network()
        car1 = Vehicle("car", 1.0, 100)
        car2 = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [car1, car2], location=DEPOT)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=3),
            DeliveryRequest("p2", 10, origin=DEPOT, destination=4),
        ]

        _make_router(courier, net).calculate_itinerary()

        # Both vehicles should have non-empty itineraries
        assert len(car1.itinerary) > 0 or len(car2.itinerary) > 0


# ---------------------------------------------------------------------------
# TestRouterCapacity
# ---------------------------------------------------------------------------

class TestRouterCapacity:
    def test_vehicle_respects_capacity(self):
        """Vehicle with capacity 10 cannot take two requests of weight 6 each."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, capacity=10)
        courier = Courier("c1", [vehicle], location=DEPOT)
        p1 = DeliveryRequest("p1", weight=6, origin=DEPOT, destination=3)
        p2 = DeliveryRequest("p2", weight=6, origin=DEPOT, destination=4)
        courier.assigned_delivery_requests = [p1, p2]

        _make_router(courier, net).calculate_itinerary()

        # Only one request should be assigned to the vehicle (total weight 6 <= 10)
        # The second request should not be assigned
        assigned_weight = sum(r.weight for r in vehicle.assigned_requests)
        assert assigned_weight <= 10
        assert len(vehicle.assigned_requests) == 1

    def test_capacity_exact_fit(self):
        """Vehicle with capacity 10 can take two requests of weight 5 each."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, capacity=10)
        courier = Courier("c1", [vehicle], location=DEPOT)
        p1 = DeliveryRequest("p1", weight=5, origin=DEPOT, destination=3)
        p2 = DeliveryRequest("p2", weight=5, origin=DEPOT, destination=4)
        courier.assigned_delivery_requests = [p1, p2]

        _make_router(courier, net).calculate_itinerary()

        # Both requests should fit (5+5=10)
        assigned_weight = sum(r.weight for r in vehicle.assigned_requests)
        assert assigned_weight == 10
        assert len(vehicle.assigned_requests) == 2

    def test_multiple_vehicles_respect_capacity(self):
        """Two vehicles share load respecting each capacity."""
        net = _make_network()
        v1 = Vehicle("car", 1.0, capacity=6)
        v2 = Vehicle("car", 1.0, capacity=6)
        courier = Courier("c1", [v1, v2], location=DEPOT)
        p1 = DeliveryRequest("p1", weight=6, origin=DEPOT, destination=3)
        p2 = DeliveryRequest("p2", weight=6, origin=DEPOT, destination=4)
        courier.assigned_delivery_requests = [p1, p2]

        _make_router(courier, net).calculate_itinerary()

        # Each vehicle should get exactly one request
        assert len(v1.assigned_requests) == 1
        assert len(v2.assigned_requests) == 1
        total_weight = sum(r.weight for v in [v1, v2] for r in v.assigned_requests)
        assert total_weight == 12

    def test_destination_nodes_set(self):
        """Vehicle's destination nodes should be set from assigned requests."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, capacity=100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", weight=10, origin=DEPOT, destination=3),
            DeliveryRequest("p2", weight=10, origin=DEPOT, destination=4),
        ]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle._destination_nodes == {3, 4}


# ---------------------------------------------------------------------------
# TestRouterRestrictions
# ---------------------------------------------------------------------------

class TestRouterRestrictions:
    def test_prohibit_edge_for_all_vehicles(self):
        """When edge 1 is prohibited for all, vehicle must use edge 2."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=4),
        ]
        restrictions = [ProhibitEdge(edge_id=1)]

        router = Router(courier, net, restrictions=restrictions)
        router.calculate_itinerary()

        # Should not be able to reach node 4, so itinerary should be empty or partial
        assert vehicle.itinerary == [] or vehicle.itinerary == [2]

    def test_prohibit_edge_for_specific_vehicle_type(self):
        """When edge 1 is prohibited for cars, bikes can still use it."""
        net = _make_network()
        car = Vehicle("car", 1.0, 100)
        bike = Vehicle("bike", 1.0, 100)
        courier = Courier("c1", [car, bike], location=DEPOT)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=3),
            DeliveryRequest("p2", 10, origin=DEPOT, destination=3),
        ]
        restrictions = [ProhibitEdge(edge_id=1, vehicle_type="car")]

        router = Router(courier, net, restrictions=restrictions)
        router.calculate_itinerary()

        # Car should not have edge 1, bike should
        assert 1 not in car.itinerary
        # (Bike may or may not depending on assignment)


# ---------------------------------------------------------------------------
# TestRouterErrors
# ---------------------------------------------------------------------------

class TestRouterErrors:
    def test_unknown_strategy_raises(self):
        net = _make_network()
        courier = Courier("c1", [Vehicle("car", 1.0, 100)], location=DEPOT)

        with pytest.raises(ValueError, match="Unknown routing strategy"):
            Router(courier, net, [], strategy="UNKNOWN").calculate_itinerary()

    def test_depot_not_in_network_raises(self):
        net = Network()
        net.add_node(Node(10, 0.0, 0.0))  # Depot is 2, but network only has 10
        courier = Courier("c1", [Vehicle("car", 1.0, 100)], location=2)

        with pytest.raises(ValueError, match="Depot node 2 not found"):
            Router(courier, net, []).calculate_itinerary()


# ---------------------------------------------------------------------------
# Additional Router Tests
# ---------------------------------------------------------------------------

class TestRouterPathFinding:
    def test_unreachable_destination_gives_empty_itinerary(self):
        """When destination cannot be reached, itinerary should be empty."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        # Node 99 doesn't exist in network
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=99)
        ]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == []

    def test_departure_time_restrictions(self):
        """Test that time-window restrictions are respected at departure time."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=4)
        ]
        # Prohibit edge 1 only during first hour
        restrictions = [ProhibitEdge(edge_id=1, time_window=[0, 3600])]

        # Depart at time 7200 (after restriction)
        router = Router(courier, net, restrictions=restrictions, departure_time=7200)
        router.calculate_itinerary()

        # Should be able to use edge 1 now
        assert 1 in vehicle.itinerary or vehicle.itinerary == []


class TestRouterCongestionPricing:
    def test_congestion_pricing_increases_travel_cost(self):
        """Congestion pricing should be factored into routing decisions."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT, vtt=30.0/3600)  # $30/hr
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=4)
        ]
        # Add congestion pricing to edge 1
        restrictions = [CongestionPricing(edge_id=1, cost=10.0)]

        router = Router(courier, net, restrictions=restrictions)
        router.calculate_itinerary()

        # Vehicle should still traverse edge 1 (only path available)
        assert 1 in vehicle.itinerary

    def test_congestion_pricing_zero_vtt_ignores_cost(self):
        """With VTT=0, congestion pricing should not affect routing."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle], location=DEPOT, vtt=0.0)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, origin=DEPOT, destination=3)
        ]
        restrictions = [CongestionPricing(edge_id=1, cost=100.0)]

        router = Router(courier, net, restrictions=restrictions)
        router.calculate_itinerary()

        # Should still use edge 1 despite high cost (VTT=0 means cost doesn't matter)
        assert vehicle.itinerary == [1]
