"""Tests for OR-Tools routing strategy.

This module tests the ORToolsRouterStrategy implementation.
"""

import pytest
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.market import Courier, DeliveryRequest
from parcel_delivery_two.agents import CourierVehicle
from parcel_delivery_two.routing import ORToolsRouterStrategy


class TestORToolsRouterStrategy:
    """Test cases for ORToolsRouterStrategy."""

    @pytest.fixture
    def simple_network(self):
        """Create a simple 3-node network for testing."""
        network = Network()

        # Nodes: 0 (depot), 1, 2
        network.add_node(Node(0, 0.0, 0.0))
        network.add_node(Node(1, 100.0, 0.0))
        network.add_node(Node(2, 200.0, 0.0))

        # Edges: 0->1 (id=0), 1->2 (id=1), 0->2 (id=2)
        network.add_edge(Edge(0, 0, 1, 100.0, 10.0))  # 10 seconds
        network.add_edge(Edge(1, 1, 2, 100.0, 10.0))  # 10 seconds
        network.add_edge(Edge(2, 0, 2, 200.0, 10.0))  # 20 seconds (longer)

        return network

    @pytest.fixture
    def courier_with_vehicles(self, simple_network):
        """Create a courier with vehicles at depot (node 0)."""
        vehicles = [
            CourierVehicle("car", travel_time_factor=1.0, capacity=100),
            CourierVehicle("car", travel_time_factor=1.0, capacity=100),
        ]
        courier = Courier("test_courier", vehicles=vehicles, location=0)
        return courier

    def test_ortools_basic_routing(self, simple_network, courier_with_vehicles):
        """Test basic routing with OR-Tools produces valid itineraries."""
        # Create delivery requests
        requests = [
            DeliveryRequest("parcel_1", weight=10, origin=0, destination=1),
            DeliveryRequest("parcel_2", weight=10, origin=0, destination=2),
        ]
        courier_with_vehicles.assigned_delivery_requests = requests

        # Create router strategy
        strategy = ORToolsRouterStrategy(
            courier=courier_with_vehicles,
            network=simple_network,
            restrictions=[],
            departure_time=0.0,
        )

        # Calculate itinerary
        strategy.calculate_itinerary()

        # Verify vehicles have itineraries
        for vehicle in courier_with_vehicles.vehicles:
            assert vehicle.itinerary is not None
            assert isinstance(vehicle.itinerary, list)

        # Verify all requests are assigned
        all_assigned = []
        for vehicle in courier_with_vehicles.vehicles:
            all_assigned.extend(vehicle.assigned_requests)

        assert len(all_assigned) == 2
        request_names = {r.name for r in all_assigned}
        assert request_names == {"parcel_1", "parcel_2"}

    def test_ortools_respects_capacity(self, simple_network):
        """Test OR-Tools respects vehicle capacity constraints."""
        vehicles = [
            CourierVehicle("car", travel_time_factor=1.0, capacity=15),
            CourierVehicle("car", travel_time_factor=1.0, capacity=100),
        ]
        courier = Courier("test_courier", vehicles=vehicles, location=0)

        # Create requests: one large (15), one small (5)
        requests = [
            DeliveryRequest("large_parcel", weight=15, origin=0, destination=1),
            DeliveryRequest("small_parcel", weight=5, origin=0, destination=2),
        ]
        courier.assigned_delivery_requests = requests

        strategy = ORToolsRouterStrategy(
            courier=courier,
            network=simple_network,
            restrictions=[],
            departure_time=0.0,
        )

        strategy.calculate_itinerary()

        # Check capacities are respected
        total_weights = []
        for vehicle in courier.vehicles:
            total_weight = sum(r.weight for r in vehicle.assigned_requests)
            total_weights.append(total_weight)
            assert total_weight <= vehicle.capacity

        # Both parcels should be assigned (total 20, capacities 15+100=115)
        assert sum(len(v.assigned_requests) for v in courier.vehicles) == 2

    def test_ortools_no_departure_time_raises(self, simple_network, courier_with_vehicles):
        """Test that ORToolsRouterStrategy requires departure_time."""
        with pytest.raises(ValueError, match="requires departure_time"):
            ORToolsRouterStrategy(
                courier=courier_with_vehicles,
                network=simple_network,
                restrictions=[],
                departure_time=None,
            )

    def test_ortools_no_requests(self, simple_network, courier_with_vehicles):
        """Test OR-Tools handles empty request list."""
        courier_with_vehicles.assigned_delivery_requests = []

        strategy = ORToolsRouterStrategy(
            courier=courier_with_vehicles,
            network=simple_network,
            restrictions=[],
            departure_time=0.0,
        )

        strategy.calculate_itinerary()

        # All vehicles should have empty itineraries
        for vehicle in courier_with_vehicles.vehicles:
            assert vehicle.itinerary == []
            assert vehicle.assigned_requests == []

    def test_ortools_single_vehicle_type(self, simple_network):
        """Test OR-Tools works with a single vehicle."""
        vehicles = [CourierVehicle("truck", travel_time_factor=1.0, capacity=100)]
        courier = Courier("test_courier", vehicles=vehicles, location=0)

        requests = [
            DeliveryRequest("parcel_1", weight=10, origin=0, destination=1),
            DeliveryRequest("parcel_2", weight=10, origin=0, destination=2),
        ]
        courier.assigned_delivery_requests = requests

        strategy = ORToolsRouterStrategy(
            courier=courier,
            network=simple_network,
            restrictions=[],
            departure_time=0.0,
        )

        strategy.calculate_itinerary()

        # Single vehicle should get all requests
        assert len(courier.vehicles[0].assigned_requests) == 2
        assert len(courier.vehicles[0].itinerary) > 0
