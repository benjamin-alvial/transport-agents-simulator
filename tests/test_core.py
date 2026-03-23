import pytest
from unittest.mock import Mock, patch, MagicMock
import heapq

from parcel_delivery_two.core.kernel import Kernel
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.agents.courier_vehicle import CourierVehicle
from parcel_delivery_two.agents.bus import Bus
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def kernel():
    """Fresh Kernel instance."""
    return Kernel()


@pytest.fixture
def mock_network():
    """Minimal network for testing."""
    net = Network()
    net.add_node(Node(1, x=0.0, y=0.0))
    net.add_node(Node(2, x=1.0, y=0.0))
    net.add_edge(Edge(10, from_node=1, to_node=2, distance=100.0, free_flow_speed=10.0))
    return net


@pytest.fixture
def mock_courier():
    """Courier with one vehicle for testing."""
    vehicle = CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100)
    courier = Courier("courier_1", vehicles=[vehicle], location=1)
    return courier


@pytest.fixture
def mock_bus():
    """Bus entity for testing."""
    return Bus("bus_1", itinerary=[10], travel_time_factor=2.0)


# -----------------------------------------------------------------------------
# Kernel Initialization
# -----------------------------------------------------------------------------

class TestKernelInitialization:
    def test_current_time_starts_at_zero(self, kernel):
        assert kernel.current_time == 0.0

    def test_event_queue_empty(self, kernel):
        assert kernel._event_queue == []

    def test_event_counter_zero(self, kernel):
        assert kernel._event_counter == 0

    def test_network_none(self, kernel):
        assert kernel.network is None

    def test_entities_empty(self, kernel):
        assert kernel._entities == []

    def test_loggers_empty(self, kernel):
        assert kernel.loggers == []

    def test_restrictions_empty(self, kernel):
        assert kernel.restrictions == []

    def test_couriers_empty(self, kernel):
        assert kernel._couriers == {}

    def test_metrics_collector_none_by_default(self, kernel):
        assert kernel.metrics_collector is None

    def test_metrics_collector_can_be_set(self):
        mock_mc = Mock()
        k = Kernel(metrics_collector=mock_mc)
        assert k.metrics_collector is mock_mc


# -----------------------------------------------------------------------------
# initialize_loggers
# -----------------------------------------------------------------------------

class TestKernelInitializeLoggers:
    def test_creates_edge_logger(self, kernel):
        kernel.initialize_loggers()
        from parcel_delivery_two.loggers.edge_logger import EdgeLogger
        assert any(isinstance(l, EdgeLogger) for l in kernel.loggers)

    def test_creates_event_logger(self, kernel):
        kernel.initialize_loggers()
        from parcel_delivery_two.loggers.event_logger import EventLogger
        assert any(isinstance(l, EventLogger) for l in kernel.loggers)

    def test_creates_both_loggers(self, kernel):
        kernel.initialize_loggers()
        assert len(kernel.loggers) == 2


# -----------------------------------------------------------------------------
# set_network
# -----------------------------------------------------------------------------

class TestKernelSetNetwork:
    def test_sets_network(self, kernel, mock_network):
        kernel.set_network(mock_network)
        assert kernel.network is mock_network

    def test_overwrites_existing_network(self, kernel, mock_network):
        other_network = Network()
        kernel.set_network(other_network)
        kernel.set_network(mock_network)
        assert kernel.network is mock_network


# -----------------------------------------------------------------------------
# set_restrictions
# -----------------------------------------------------------------------------

class TestKernelSetRestrictions:
    def test_sets_empty_list(self, kernel):
        kernel.set_restrictions([])
        assert kernel.restrictions == []

    def test_sets_single_restriction(self, kernel):
        restriction = ProhibitEdge(edge_id=1)
        kernel.set_restrictions([restriction])
        assert kernel.restrictions == [restriction]

    def test_sets_multiple_restrictions(self, kernel):
        r1 = ProhibitEdge(edge_id=1)
        r2 = CongestionPricing(edge_id=2, cost=1.0)
        kernel.set_restrictions([r1, r2])
        assert kernel.restrictions == [r1, r2]

    def test_overwrites_existing_restrictions(self, kernel):
        r1 = ProhibitEdge(edge_id=1)
        r2 = ProhibitEdge(edge_id=2)
        kernel.set_restrictions([r1])
        kernel.set_restrictions([r2])
        assert kernel.restrictions == [r2]


# -----------------------------------------------------------------------------
# register_courier
# -----------------------------------------------------------------------------

class TestKernelRegisterCourier:
    def test_adds_to_entities(self, kernel, mock_courier):
        kernel.register_courier(mock_courier)
        assert mock_courier in kernel._entities

    def test_adds_to_couriers_dict(self, kernel, mock_courier):
        kernel.register_courier(mock_courier)
        assert kernel._couriers["courier_1"] is mock_courier

    def test_injects_kernel_into_vehicles(self, kernel, mock_courier):
        kernel.register_courier(mock_courier)
        for vehicle in mock_courier.vehicles:
            assert vehicle._kernel is kernel

    def test_sets_entity_id_on_vehicles(self, kernel, mock_courier):
        kernel.register_courier(mock_courier)
        vehicle = mock_courier.vehicles[0]
        assert vehicle.entity_id == "courier_1_car_0"

    def test_multiple_vehicles_get_unique_ids(self, kernel):
        v1 = CourierVehicle("car", 1.0, 100)
        v2 = CourierVehicle("bike", 0.5, 20)
        courier = Courier("courier_2", vehicles=[v1, v2], location=1)
        kernel.register_courier(courier)
        assert v1.entity_id == "courier_2_car_0"
        assert v2.entity_id == "courier_2_bike_1"


# -----------------------------------------------------------------------------
# get_courier
# -----------------------------------------------------------------------------

class TestKernelGetCourier:
    def test_returns_none_when_not_found(self, kernel):
        assert kernel.get_courier("nonexistent") is None

    def test_returns_courier_when_found(self, kernel, mock_courier):
        kernel.register_courier(mock_courier)
        assert kernel.get_courier("courier_1") is mock_courier

    def test_returns_correct_courier_among_many(self, kernel):
        c1 = Courier("c1", [CourierVehicle("car", 1.0, 100)], location=1)
        c2 = Courier("c2", [CourierVehicle("bike", 0.5, 20)], location=2)
        kernel.register_courier(c1)
        kernel.register_courier(c2)
        assert kernel.get_courier("c2") is c2


# -----------------------------------------------------------------------------
# register_entity
# -----------------------------------------------------------------------------

class TestKernelRegisterEntity:
    def test_adds_to_entities(self, kernel, mock_bus):
        kernel.register_entity(mock_bus)
        assert mock_bus in kernel._entities

    def test_injects_kernel(self, kernel, mock_bus):
        kernel.register_entity(mock_bus)
        assert mock_bus._kernel is kernel

    def test_works_with_any_entity(self, kernel):
        class DummyEntity:
            pass
        entity = DummyEntity()
        kernel.register_entity(entity)
        assert entity in kernel._entities
        assert entity._kernel is kernel


# -----------------------------------------------------------------------------
# schedule
# -----------------------------------------------------------------------------

class TestKernelSchedule:
    def test_adds_event_to_queue(self, kernel):
        action = Mock()
        kernel.schedule(10.0, action)
        assert len(kernel._event_queue) == 1

    def test_event_has_correct_time(self, kernel):
        action = Mock()
        kernel.schedule(10.0, action)
        fire_at, _, _ = kernel._event_queue[0]
        assert fire_at == 10.0

    def test_increments_event_counter(self, kernel):
        action = Mock()
        kernel.schedule(1.0, action)
        assert kernel._event_counter == 1
        kernel.schedule(2.0, action)
        assert kernel._event_counter == 2

    def test_negative_delay_raises(self, kernel):
        action = Mock()
        with pytest.raises(ValueError, match="Delay must be non-negative"):
            kernel.schedule(-1.0, action)

    def test_zero_delay_allowed(self, kernel):
        action = Mock()
        kernel.schedule(0.0, action)
        assert len(kernel._event_queue) == 1

    def test_events_ordered_by_time(self, kernel):
        actions = [Mock() for _ in range(3)]
        kernel.schedule(30.0, actions[0])
        kernel.schedule(10.0, actions[1])
        kernel.schedule(20.0, actions[2])
        # Queue is a heap - verify by popping all elements in order
        times = []
        while kernel._event_queue:
            fire_at, _, _ = heapq.heappop(kernel._event_queue)
            times.append(fire_at)
        assert times == sorted(times)

    def test_schedules_relative_to_current_time(self, kernel):
        kernel.current_time = 100.0
        action = Mock()
        kernel.schedule(50.0, action)
        fire_at, _, _ = kernel._event_queue[0]
        assert fire_at == 150.0


# -----------------------------------------------------------------------------
# run
# -----------------------------------------------------------------------------

class TestKernelRun:
    def test_processes_single_event(self, kernel):
        action = Mock()
        kernel.schedule(10.0, action)
        kernel.run(until=100.0)
        action.assert_called_once()

    def test_processes_multiple_events(self, kernel):
        actions = [Mock() for _ in range(3)]
        kernel.schedule(10.0, actions[0])
        kernel.schedule(20.0, actions[1])
        kernel.schedule(30.0, actions[2])
        kernel.run(until=100.0)
        for action in actions:
            action.assert_called_once()

    def test_events_processed_in_time_order(self, kernel):
        order = []
        def make_action(i):
            def action():
                order.append(i)
            return action
        
        kernel.schedule(30.0, make_action(2))
        kernel.schedule(10.0, make_action(0))
        kernel.schedule(20.0, make_action(1))
        kernel.run(until=100.0)
        assert order == [0, 1, 2]

    def test_stops_at_until_time(self, kernel):
        action_late = Mock()
        kernel.schedule(50.0, action_late)
        kernel.run(until=30.0)
        action_late.assert_not_called()

    def test_stops_when_queue_empty(self, kernel):
        action = Mock()
        kernel.schedule(10.0, action)
        kernel.run(until=1000.0)  # Long after event
        action.assert_called_once()
        assert kernel.current_time == 1000.0

    def test_updates_current_time_per_event(self, kernel):
        times = []
        def record_time():
            times.append(kernel.current_time)
        
        kernel.schedule(10.0, record_time)
        kernel.schedule(30.0, record_time)
        kernel.run(until=100.0)
        assert times == [10.0, 30.0]

    def test_final_current_time_is_until(self, kernel):
        kernel.schedule(10.0, Mock())
        kernel.run(until=50.0)
        assert kernel.current_time == 50.0

    def test_no_events_sets_current_time_to_until(self, kernel):
        kernel.run(until=100.0)
        assert kernel.current_time == 100.0

    def test_dumps_loggers_after_run_integration(self, kernel, tmp_path):
        """Test that loggers are actually dumped after run."""
        import os
        # Create mock logger that tracks if dump_to_csv was called
        mock_logger = Mock()
        mock_logger.dump_to_csv = Mock()
        kernel.loggers.append(mock_logger)
        
        kernel.schedule(1.0, Mock())
        kernel.run(until=10.0)
        
        mock_logger.dump_to_csv.assert_called_once()

    def test_events_can_schedule_more_events(self, kernel):
        """Events scheduled during run are processed if within until."""
        def schedule_next():
            kernel.schedule(5.0, inner_action)
        
        inner_action = Mock()
        kernel.schedule(1.0, schedule_next)
        kernel.run(until=20.0)
        inner_action.assert_called_once()


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestKernelIntegration:
    def test_full_simulation_workflow(self, kernel, mock_network, mock_courier, tmp_path):
        """Test a complete simulation setup and run."""
        import os
        # Create output directory to avoid FileNotFoundError
        os.makedirs("output", exist_ok=True)
        
        # Setup
        kernel.set_network(mock_network)
        kernel.initialize_loggers()
        kernel.register_courier(mock_courier)
        
        # Create a simple test action
        actions_executed = []
        def test_action():
            actions_executed.append(kernel.current_time)
        
        kernel.schedule(10.0, test_action)
        kernel.schedule(20.0, test_action)
        kernel.run(until=100.0)
        
        assert actions_executed == [10.0, 20.0]
        assert kernel.current_time == 100.0

    def test_multiple_entities_interaction(self, kernel, mock_network):
        """Test multiple couriers and buses in same simulation."""
        kernel.set_network(mock_network)
        
        # Create multiple couriers
        c1 = Courier("c1", [CourierVehicle("car", 1.0, 100)], location=1)
        c2 = Courier("c2", [CourierVehicle("bike", 0.5, 20)], location=1)
        bus = Bus("bus_1", itinerary=[10], travel_time_factor=2.0)
        
        kernel.register_courier(c1)
        kernel.register_courier(c2)
        kernel.register_entity(bus)
        
        # All entities should be tracked
        assert len(kernel._entities) == 3
        assert kernel.get_courier("c1") is c1
        assert kernel.get_courier("c2") is c2
        assert bus._kernel is kernel

    def test_restrictions_with_network(self, kernel, mock_network):
        """Test that restrictions can reference network edges."""
        kernel.set_network(mock_network)
        restriction = ProhibitEdge(edge_id=10, vehicle_type="car")
        kernel.set_restrictions([restriction])
        
        # Verify the restriction is stored
        assert len(kernel.restrictions) == 1
        assert kernel.restrictions[0].edge_id == 10
