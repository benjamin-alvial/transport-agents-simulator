import pytest

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.market.vehicle import Vehicle
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.routing.router import Router


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
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 3)]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == [1]

    def test_single_vehicle_chained_request(self):
        """Vehicle visiting node 4 must traverse edges 1 then 2."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 4)]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == [1, 2]

    def test_single_vehicle_two_requests_ordered_nearest_first(self):
        """With stops at node 3 and 4, the nearest (3) is visited before 4."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        # Intentionally put farther stop first to verify nearest-neighbour reordering
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, 4),
            DeliveryRequest("p2", 10, 3),
        ]

        _make_router(courier, net).calculate_itinerary()

        # Optimal tour: 2→3 (edge 1) then 3→4 (edge 2)
        assert vehicle.itinerary == [1, 2]

    def test_no_requests_gives_empty_itinerary(self):
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = []

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == []

    def test_destination_equals_depot_gives_empty_itinerary(self):
        """A delivery whose destination is the depot itself needs no travel."""
        net = _make_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 2)]

        _make_router(courier, net).calculate_itinerary()

        assert vehicle.itinerary == []

    def test_itinerary_set_on_all_vehicles(self):
        """After routing, every vehicle has the itinerary attribute populated."""
        net = _make_network()
        vehicles = [Vehicle("car", 1.0, 50), Vehicle("car", 1.0, 50)]
        courier = Courier("c1", vehicles)
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, 3),
            DeliveryRequest("p2", 10, 3),
        ]

        _make_router(courier, net).calculate_itinerary()

        for v in vehicles:
            assert hasattr(v, "itinerary")
            assert isinstance(v.itinerary, list)


# ---------------------------------------------------------------------------
# TestRequestAssignment
# ---------------------------------------------------------------------------

class TestRequestAssignment:
    def test_requests_split_across_vehicles(self):
        """Two vehicles of capacity 20 split 4 requests of weight 10 (2 each)."""
        net = _make_network()
        v1 = Vehicle("car", 1.0, 20)
        v2 = Vehicle("car", 1.0, 20)
        courier = Courier("c1", [v1, v2])
        courier.assigned_delivery_requests = [
            DeliveryRequest(f"p{i}", 10, 3) for i in range(4)
        ]

        router = _make_router(courier, net)
        groups = router._assign_requests_to_vehicles()

        assert len(groups[0]) == 2
        assert len(groups[1]) == 2

    def test_first_vehicle_filled_before_second(self):
        """Greedy fill: vehicle 0 is packed before vehicle 1 receives any request."""
        net = _make_network()
        v1 = Vehicle("car", 1.0, 30)
        v2 = Vehicle("car", 1.0, 30)
        courier = Courier("c1", [v1, v2])
        courier.assigned_delivery_requests = [
            DeliveryRequest(f"p{i}", 10, 3) for i in range(3)
        ]

        router = _make_router(courier, net)
        groups = router._assign_requests_to_vehicles()

        assert len(groups[0]) == 3
        assert len(groups[1]) == 0

    def test_vehicle_with_no_capacity_receives_nothing(self):
        """A vehicle whose capacity is 0 is never assigned a request."""
        net = _make_network()
        v_empty = Vehicle("car", 1.0, 0)
        v_normal = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [v_empty, v_normal])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 3)]

        router = _make_router(courier, net)
        groups = router._assign_requests_to_vehicles()

        assert len(groups[0]) == 0
        assert len(groups[1]) == 1


# ---------------------------------------------------------------------------
# TestRouterErrors
# ---------------------------------------------------------------------------

class TestRouterErrors:
    def test_unknown_strategy_raises(self):
        net = _make_network()
        courier = Courier("c1", [])
        router = Router(courier, net, [], strategy="UNKNOWN")
        with pytest.raises(ValueError, match="Unknown routing strategy"):
            router.calculate_itinerary()

    def test_missing_depot_raises(self):
        """ValueError when the network does not contain the depot node."""
        net = Network()
        net.add_node(Node(10, 0.0, 0.0))
        net.add_node(Node(11, 1.0, 0.0))
        net.add_edge(Edge(1, 10, 11, 100.0, 10.0))
        courier = Courier("c1", [Vehicle("car", 1.0, 100)])
        router = Router(courier, net, [], strategy="DEFAULT")
        with pytest.raises(ValueError, match="Depot node"):
            router.calculate_itinerary()


# ---------------------------------------------------------------------------
# TestRestrictions
# ---------------------------------------------------------------------------
#
# Network with two paths from 2 to 4:
#   fast path : 2 --(e1)--> 3 --(e2)--> 4   total cost 20 s
#   slow path : 2 --(e3)--> 4              total cost 30 s
# Without restrictions the fast path (e1, e2) is preferred.
# Blocking e1 forces the slow path (e3).
# ---------------------------------------------------------------------------

def _make_forked_network() -> Network:
    net = Network()
    net.add_node(Node(2, 0.0, 0.0))
    net.add_node(Node(3, 1.0, 0.0))
    net.add_node(Node(4, 2.0, 0.0))
    # fast path via node 3 (cost 10+10 = 20 s)
    net.add_edge(Edge(edge_id=1, from_node=2, to_node=3, distance=100.0, free_flow_speed=10.0))
    net.add_edge(Edge(edge_id=2, from_node=3, to_node=4, distance=100.0, free_flow_speed=10.0))
    # slow direct path (cost 30 s)
    net.add_edge(Edge(edge_id=3, from_node=2, to_node=4, distance=300.0, free_flow_speed=10.0))
    return net


class TestRestrictions:
    def test_no_restrictions_uses_fast_path(self):
        net = _make_forked_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 4)]

        Router(courier, net, restrictions=[]).calculate_itinerary()

        assert vehicle.itinerary == [1, 2]

    def test_prohibit_all_forces_detour(self):
        """Blocking e1 for all vehicles makes every vehicle use the slow path."""
        net = _make_forked_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 4)]

        Router(courier, net, restrictions=[ProhibitEdge(1)]).calculate_itinerary()

        assert vehicle.itinerary == [3]

    def test_prohibit_specific_type_forces_detour_for_that_type(self):
        """e1 blocked for 'car' → car uses slow path; bike still uses fast path."""
        net = _make_forked_network()
        # cap car at 10 so the second request falls to bike
        car = Vehicle("car", 1.0, 10)
        bike = Vehicle("bike", 1.0, 100)
        courier = Courier("c1", [car, bike])
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, 4),
            DeliveryRequest("p2", 10, 4),
        ]

        Router(courier, net, restrictions=[ProhibitEdge(1, "car")]).calculate_itinerary()

        assert car.itinerary == [3]     # blocked from fast path
        assert bike.itinerary == [1, 2] # unaffected

    def test_prohibit_other_type_does_not_affect_vehicle(self):
        """e1 blocked for 'truck' has no effect on 'car'."""
        net = _make_forked_network()
        vehicle = Vehicle("car", 1.0, 100)
        courier = Courier("c1", [vehicle])
        courier.assigned_delivery_requests = [DeliveryRequest("p1", 10, 4)]

        Router(courier, net, restrictions=[ProhibitEdge(1, "truck")]).calculate_itinerary()

        assert vehicle.itinerary == [1, 2]

    def test_adjacency_cached_per_vehicle_type(self):
        """Two vehicles of different types produce separate cached adjacency entries."""
        net = _make_forked_network()
        # cap car at 10 so both vehicle types each receive one request
        car = Vehicle("car", 1.0, 10)
        bike = Vehicle("bike", 1.0, 100)
        courier = Courier("c1", [car, bike])
        courier.assigned_delivery_requests = [
            DeliveryRequest("p1", 10, 4),
            DeliveryRequest("p2", 10, 4),
        ]

        router = Router(courier, net, restrictions=[ProhibitEdge(1, "car")])
        router.calculate_itinerary()

        assert "car" in router._adj
        assert "bike" in router._adj
        assert len(router._adj["car"][2]) == 1   # only e3 available
        assert len(router._adj["bike"][2]) == 2  # e1 and e3 available
