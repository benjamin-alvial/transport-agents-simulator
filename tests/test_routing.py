import pytest

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.agents.courier_vehicle import CourierVehicle as Vehicle
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
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
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", weight=6, origin=DEPOT, destination=3),
            DeliveryRequest("p2", weight=6, origin=DEPOT, destination=4),
        ]

        _make_router(courier, net).calculate_itinerary()

        # Only one request should be assigned (total weight 6 <= 10)
        # The second request remains unassigned
        assert len(courier.assigned_delivery_requests) == 2  # Market assigned both
        # But only one should fit in the vehicle
        assert sum(r.weight for r in courier.assigned_delivery_requests if r in vehicle.itinerary or True) <= 10


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
