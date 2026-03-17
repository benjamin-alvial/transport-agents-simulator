import pytest
from unittest.mock import Mock, patch, MagicMock

from parcel_delivery_two.agents.transport_vehicle import TransportVehicle
from parcel_delivery_two.agents.courier_vehicle import CourierVehicle
from parcel_delivery_two.agents.bus import Bus
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.market.delivery_request import DeliveryRequest


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_kernel():
    """Create a mock kernel for testing."""
    kernel = Mock()
    kernel.current_time = 0.0
    kernel.network = Mock()
    kernel.network.edges = {}
    kernel.schedule = Mock()
    kernel.get_courier = Mock(return_value=None)
    kernel.restrictions = []
    return kernel


@pytest.fixture
def mock_edge():
    """Create a mock edge for testing."""
    edge = Mock()
    edge.edge_id = 1
    edge.from_node = 1
    edge.to_node = 2
    edge.distance = 100.0
    edge.free_flow_speed = 10.0
    edge.travel_times = {}
    return edge


@pytest.fixture
def mock_courier():
    """Create a mock courier with VTT."""
    courier = Mock()
    courier.vtt = 30.0 / 3600  # $30/hour = $0.00833/second
    return courier


# -----------------------------------------------------------------------------
# TransportVehicle - Basic Attributes
# -----------------------------------------------------------------------------

class TestTransportVehicleBasic:
    def test_attributes(self):
        v = TransportVehicle("test_vehicle", travel_time_factor=1.5, itinerary=[1, 2, 3])
        assert v.entity_id == "test_vehicle"
        assert v.travel_time_factor == 1.5
        assert v.itinerary == [1, 2, 3]

    def test_default_itinerary(self):
        v = TransportVehicle("test_vehicle")
        assert v.itinerary == []

    def test_default_travel_time_factor(self):
        v = TransportVehicle("test_vehicle")
        assert v.travel_time_factor == 1.0

    def test_kernel_injection(self):
        v = TransportVehicle("test_vehicle")
        assert v._kernel is None
        mock_k = Mock()
        v._kernel = mock_k
        assert v._kernel is mock_k


# -----------------------------------------------------------------------------
# TransportVehicle - Travel Time Computation
# -----------------------------------------------------------------------------

class TestTransportVehicleTravelTime:
    def test_compute_travel_time_free_flow(self, mock_kernel, mock_edge):
        v = TransportVehicle("test_vehicle")
        v._kernel = mock_kernel
        
        # Free flow: 100m / 10m/s = 10s
        travel_time = v._compute_travel_time(mock_edge)
        assert travel_time == 10.0

    def test_compute_travel_time_with_factor(self, mock_kernel, mock_edge):
        v = TransportVehicle("test_vehicle", travel_time_factor=2.0)
        v._kernel = mock_kernel
        
        # With factor: 10s * 2 = 20s
        travel_time = v._compute_travel_time(mock_edge)
        assert travel_time == 20.0

    def test_compute_travel_time_with_historical_data(self, mock_kernel, mock_edge):
        v = TransportVehicle("test_vehicle", travel_time_factor=1.0)
        v._kernel = mock_kernel
        v._kernel.current_time = 450.0  # In bin 0 (0-900s)
        
        # Historical data for bin 0
        mock_edge.travel_times = {0: 15.0}
        
        travel_time = v._compute_travel_time(mock_edge)
        assert travel_time == 15.0

    def test_compute_travel_time_historical_with_factor(self, mock_kernel, mock_edge):
        v = TransportVehicle("test_vehicle", travel_time_factor=2.0)
        v._kernel = mock_kernel
        v._kernel.current_time = 450.0
        
        mock_edge.travel_times = {0: 15.0}
        
        travel_time = v._compute_travel_time(mock_edge)
        assert travel_time == 30.0


# -----------------------------------------------------------------------------
# TransportVehicle - Congestion Pricing
# -----------------------------------------------------------------------------

class TestTransportVehicleCongestionPricing:
    def test_compute_edge_cost_not_courier_vehicle(self, mock_kernel):
        """Bus or non-courier vehicles should have zero cost."""
        v = TransportVehicle("bus_1")
        v._kernel = mock_kernel
        
        cost = v._compute_edge_cost(1)
        assert cost == 0.0

    def test_compute_edge_cost_no_courier(self, mock_kernel):
        """Courier vehicle without valid courier should have zero cost."""
        v = TransportVehicle("courier1_car_0")
        v._kernel = mock_kernel
        mock_kernel.get_courier.return_value = None
        
        cost = v._compute_edge_cost(1)
        assert cost == 0.0

    def test_compute_edge_cost_zero_vtt(self, mock_kernel):
        """Courier with VTT=0 should have zero cost."""
        v = TransportVehicle("courier1_car_0")
        v._kernel = mock_kernel
        
        courier = Mock()
        courier.vtt = 0.0
        mock_kernel.get_courier.return_value = courier
        
        cost = v._compute_edge_cost(1)
        assert cost == 0.0

    def test_compute_edge_cost_with_congestion_pricing(self, mock_kernel, mock_courier):
        """Test cost computation with congestion pricing restrictions."""
        from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing
        
        v = TransportVehicle("courier1_car_0")
        v._kernel = mock_kernel
        v._kernel.current_time = 100.0
        mock_kernel.get_courier.return_value = mock_courier
        
        # Add congestion pricing restriction
        restriction = CongestionPricing(edge_id=1, cost=5.0)
        mock_kernel.restrictions = [restriction]
        
        cost = v._compute_edge_cost(1)
        assert cost == 5.0

    def test_compute_edge_cost_different_edge(self, mock_kernel, mock_courier):
        """Cost should be zero for edges without pricing."""
        from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing
        
        v = TransportVehicle("courier1_car_0")
        v._kernel = mock_kernel
        mock_kernel.get_courier.return_value = mock_courier
        
        # Pricing on edge 1, querying edge 2
        restriction = CongestionPricing(edge_id=1, cost=5.0)
        mock_kernel.restrictions = [restriction]
        
        cost = v._compute_edge_cost(2)
        assert cost == 0.0


# -----------------------------------------------------------------------------
# TransportVehicle - DES Journey Simulation
# -----------------------------------------------------------------------------

class TestTransportVehicleJourney:
    @patch('parcel_delivery_two.agents.transport_vehicle.EventLogger')
    def test_start_journey_logs_event(self, mock_logger_class, mock_kernel, mock_edge):
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger
        
        v = TransportVehicle("test", itinerary=[1])
        v._kernel = mock_kernel
        mock_kernel.network.edges = {1: mock_edge}
        
        v.start_journey()
        
        # Should log journey start
        mock_logger.log_entry.assert_called()

    def test_advance_schedules_first_edge(self, mock_kernel, mock_edge):
        v = TransportVehicle("test", itinerary=[1])
        v._kernel = mock_kernel
        mock_kernel.network.edges = {1: mock_edge}
        
        v._advance(0)
        
        # Should schedule the edge traversal
        assert mock_kernel.schedule.called
        args = mock_kernel.schedule.call_args
        assert args[0][0] == 10.0  # Travel time

    def test_advance_completes_journey(self, mock_kernel, mock_edge):
        v = TransportVehicle("test", itinerary=[1])
        v._kernel = mock_kernel
        mock_kernel.network.edges = {1: mock_edge}
        
        # Manually trigger completion of the only edge
        v._complete_edge(1, 0, 10.0)
        
        # Journey should be complete, _advance called again with index 1
        # which is >= len(itinerary), so it logs completion

    def test_complete_edge_records_metrics(self, mock_kernel, mock_edge):
        with patch('parcel_delivery_two.agents.transport_vehicle.MetricsCollector') as mock_mc_class:
            with patch.object(TransportVehicle, '_advance'):
                mock_mc = Mock()
                mock_mc_class.return_value = mock_mc
                
                v = TransportVehicle("test", itinerary=[1, 2])
                v._kernel = mock_kernel
                mock_kernel.network.edges = {1: mock_edge}
                
                v._complete_edge(1, 0, 10.0)
                
                # Should record edge completion
                assert mock_mc.record_edge_completion.called


# -----------------------------------------------------------------------------
# TransportVehicle - Logging
# -----------------------------------------------------------------------------

class TestTransportVehicleLogging:
    @patch('parcel_delivery_two.agents.transport_vehicle.EdgeLogger')
    def test_on_edge_entered(self, mock_logger_class, mock_kernel, mock_edge):
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger
        
        v = TransportVehicle("test")
        v._kernel = mock_kernel
        v._kernel.current_time = 100.0
        mock_kernel.network.edges = {1: mock_edge}
        
        v._on_edge_entered(1)
        
        mock_logger.log_entry.assert_called_once()
        args = mock_logger.log_entry.call_args[0]
        assert args[0] == 100.0  # time
        assert args[1] == "test"  # entity_id
        assert args[2] == "entry"  # action

    @patch('parcel_delivery_two.agents.transport_vehicle.EdgeLogger')
    def test_on_edge_exited(self, mock_logger_class, mock_kernel, mock_edge):
        mock_logger = Mock()
        mock_logger_class.return_value = mock_logger
        
        v = TransportVehicle("test")
        v._kernel = mock_kernel
        v._kernel.current_time = 110.0
        mock_kernel.network.edges = {1: mock_edge}
        
        v._on_edge_exited(1)
        
        mock_logger.log_entry.assert_called_once()
        args = mock_logger.log_entry.call_args[0]
        assert args[2] == "exit"


# -----------------------------------------------------------------------------
# CourierVehicle
# -----------------------------------------------------------------------------

class TestCourierVehicleBasic:
    def test_attributes(self):
        v = CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100)
        assert v.vehicle_type == "car"
        assert v.travel_time_factor == 1.0
        assert v.capacity == 100

    def test_itinerary_initializes_empty(self):
        v = CourierVehicle(vehicle_type="bike", travel_time_factor=0.5, capacity=20)
        assert v.itinerary == []

    def test_entity_id_format(self):
        v = CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100)
        assert v.entity_id == "car_vehicle"

    def test_assigned_requests_empty(self):
        v = CourierVehicle("car", 1.0, 100)
        assert v.assigned_requests == []

    def test_destination_nodes_empty(self):
        v = CourierVehicle("car", 1.0, 100)
        assert v._destination_nodes == set()


class TestCourierVehicleJourney:
    def test_start_journey_records_start_times(self, mock_kernel):
        v = CourierVehicle("car", 1.0, 100)
        v._kernel = mock_kernel
        v._kernel.current_time = 50.0
        
        # Create delivery requests
        req1 = DeliveryRequest("p1", 10, origin=1, destination=2)
        req2 = DeliveryRequest("p2", 10, origin=1, destination=3)
        v.assigned_requests = [req1, req2]
        
        with patch.object(v, '_advance'):
            with patch.object(v, '_log_event'):
                v.start_journey()
        
        # Both requests should have start_time set
        assert req1.start_time == 50.0
        assert req2.start_time == 50.0

    def test_complete_edge_records_delivery(self, mock_kernel, mock_edge):
        with patch('parcel_delivery_two.agents.courier_vehicle.EventLogger') as mock_logger_class:
            with patch('parcel_delivery_two.agents.courier_vehicle.MetricsCollector') as mock_mc_class:
                mock_logger = Mock()
                mock_logger_class.return_value = mock_logger
                mock_mc = Mock()
                mock_mc_class.return_value = mock_mc
                
                v = CourierVehicle("car", 1.0, 100)
                v._kernel = mock_kernel
                v._kernel.current_time = 200.0
                mock_kernel.network.edges = {1: mock_edge}
                
                # Setup delivery
                req = DeliveryRequest("p1", 10, origin=1, destination=2)
                req.start_time = 100.0
                v.assigned_requests = [req]
                v._destination_nodes = {2}
                v.entity_id = "courier1_car_0"
                
                # Complete the edge
                v._complete_edge(1, 0, 50.0)
                
                # Should record completion
                assert req.completion_time == 200.0
                assert mock_mc.record_delivery_completion.called
                # Delivery time should be 100s (200 - 100)
                args = mock_mc.record_delivery_completion.call_args[0]
                assert args[2] == 100.0

    def test_complete_edge_not_destination(self, mock_kernel, mock_edge):
        """Should not record delivery if not at destination."""
        with patch('parcel_delivery_two.agents.courier_vehicle.MetricsCollector') as mock_mc_class:
            mock_mc = Mock()
            mock_mc_class.return_value = mock_mc
            
            v = CourierVehicle("car", 1.0, 100)
            v._kernel = mock_kernel
            mock_kernel.network.edges = {1: mock_edge}
            
            # Destination is 2, but edge goes to node 3
            mock_edge.to_node = 3
            v._destination_nodes = {2}
            
            v._complete_edge(1, 0, 50.0)
            
            # Should not record delivery
            assert not mock_mc.record_delivery_completion.called


# -----------------------------------------------------------------------------
# Bus
# -----------------------------------------------------------------------------

class TestBusBasic:
    def test_attributes(self):
        b = Bus("bus_1", itinerary=[5, 10, 15], travel_time_factor=2.0)
        assert b.entity_id == "bus_1"
        assert b.itinerary == [5, 10, 15]
        assert b.travel_time_factor == 2.0

    def test_default_travel_time_factor(self):
        b = Bus("bus_1", itinerary=[5, 10])
        assert b.travel_time_factor == 2.0

    def test_inherits_from_transport_vehicle(self):
        b = Bus("bus_1", itinerary=[1, 2])
        assert isinstance(b, TransportVehicle)

    def test_empty_itinerary(self):
        b = Bus("bus_1", itinerary=[])
        assert b.itinerary == []


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestAgentIntegration:
    def test_courier_vehicle_full_journey_workflow(self, mock_kernel, mock_edge):
        """Test a complete courier vehicle journey with delivery."""
        with patch('parcel_delivery_two.agents.courier_vehicle.EventLogger'):
            with patch('parcel_delivery_two.agents.courier_vehicle.MetricsCollector'):
                v = CourierVehicle("car", 1.0, 100)
                v._kernel = mock_kernel
                v._kernel.current_time = 0.0
                mock_kernel.network.edges = {1: mock_edge}
                
                # Setup delivery
                req = DeliveryRequest("p1", 10, origin=1, destination=2)
                v.assigned_requests = [req]
                v._destination_nodes = {2}
                v.itinerary = [1]
                v.entity_id = "courier1_car_0"
                
                # Start journey
                v.start_journey()
                
                # Verify start time recorded
                assert req.start_time == 0.0
