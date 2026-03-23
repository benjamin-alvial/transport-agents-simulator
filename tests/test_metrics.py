import pytest
import csv
import os
from pathlib import Path
from unittest.mock import patch
from io import StringIO

from parcel_delivery_two.metrics.metrics_collector import MetricsCollector, VehicleMetrics
from parcel_delivery_two.metrics.post_simulation_metrics import (
    VehicleTypeConfig, VehicleMetricsRow, CourierMetricsRow,
    PostSimulationMetrics
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_metrics_collector():
    """Reset MetricsCollector singleton before each test."""
    MetricsCollector._instance = None
    yield
    MetricsCollector._instance = None


@pytest.fixture
def metrics():
    """Fresh MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def sample_vehicle_configs():
    """Sample vehicle configurations for testing."""
    return {
        "car": VehicleTypeConfig(
            fuel_efficiency_km_per_l=15.0,
            fuel_price_per_liter=1.80,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=25.0
        ),
        "bike": VehicleTypeConfig(
            fuel_efficiency_km_per_l=float('inf'),
            fuel_price_per_liter=0.0,
            emission_factor_g_co2_per_l=0,
            is_clean_mode=True,
            labor_cost_per_hour=20.0
        ),
        "bus": VehicleTypeConfig(
            fuel_efficiency_km_per_l=5.0,
            fuel_price_per_liter=1.80,
            emission_factor_g_co2_per_l=2600,
            is_clean_mode=False,
            labor_cost_per_hour=30.0
        )
    }


@pytest.fixture
def sample_vehicle_data():
    """Sample vehicle metrics data."""
    return [
        VehicleMetricsRow("courier1_car_0", 5000.0, 600.0, 2.50, 10, 3, 1200.0),
        VehicleMetricsRow("courier1_car_1", 3000.0, 400.0, 1.50, 6, 2, 800.0),
        VehicleMetricsRow("courier2_bike_0", 2000.0, 900.0, 0.0, 15, 5, 1500.0),
        VehicleMetricsRow("bus_1", 10000.0, 1200.0, 5.0, 20, 0, 0.0),
    ]


@pytest.fixture
def sample_courier_data():
    """Sample courier metrics data."""
    return [
        CourierMetricsRow("courier1", 8000.0, 1000.0, 4.0, 16, 5, 1000.0),
        CourierMetricsRow("courier2", 2000.0, 900.0, 0.0, 15, 5, 1500.0),
    ]


@pytest.fixture
def sample_totals_data():
    """Sample totals data."""
    return {
        "total_vehicles": 4,
        "total_couriers": 2,
        "total_distance_m": 20000.0,
        "total_travel_time_s": 3100.0,
    }


# -----------------------------------------------------------------------------
# VehicleMetrics Dataclass
# -----------------------------------------------------------------------------

class TestVehicleMetrics:
    def test_default_initialization(self):
        vm = VehicleMetrics()
        assert vm.distance_traveled == 0.0
        assert vm.travel_time == 0.0
        assert vm.edges_traversed == 0
        assert vm.monetary_cost == 0.0
        assert vm.delivery_times == []

    def test_delivery_times_initialized(self):
        vm = VehicleMetrics()
        assert isinstance(vm.delivery_times, list)
        assert vm.delivery_times is not None

    def test_get_average_delivery_time_empty(self):
        vm = VehicleMetrics()
        assert vm.get_average_delivery_time() == 0.0

    def test_get_average_delivery_time_single(self):
        vm = VehicleMetrics()
        vm.delivery_times = [100.0]
        assert vm.get_average_delivery_time() == 100.0

    def test_get_average_delivery_time_multiple(self):
        vm = VehicleMetrics()
        vm.delivery_times = [100.0, 200.0, 300.0]
        assert vm.get_average_delivery_time() == 200.0

    def test_custom_initialization(self):
        vm = VehicleMetrics(
            distance_traveled=1000.0,
            travel_time=120.0,
            edges_traversed=5,
            monetary_cost=10.0,
            delivery_times=[100.0, 200.0]
        )
        assert vm.distance_traveled == 1000.0
        assert vm.travel_time == 120.0
        assert vm.edges_traversed == 5
        assert vm.monetary_cost == 10.0
        assert vm.delivery_times == [100.0, 200.0]


# -----------------------------------------------------------------------------
# MetricsCollector - Singleton
# -----------------------------------------------------------------------------

class TestMetricsCollectorSingleton:
    def test_returns_same_instance(self):
        m1 = MetricsCollector()
        m2 = MetricsCollector()
        assert m1 is m2

    def test_initialized_flag_set(self, metrics):
        assert metrics._initialized is True

    def test_second_init_doesnt_reset(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        m2 = MetricsCollector()
        # Should still have the recorded data
        assert m2.get_total_distance() == 100.0


# -----------------------------------------------------------------------------
# MetricsCollector - Edge Completion Recording
# -----------------------------------------------------------------------------

class TestMetricsCollectorEdgeCompletion:
    def test_record_creates_vehicle_entry(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        assert "v1" in metrics._vehicle_metrics

    def test_record_updates_distance(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        assert metrics.get_total_distance() == 100.0

    def test_record_updates_travel_time(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        assert metrics.get_total_travel_time() == 10.0

    def test_record_updates_edges_traversed(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        vm = metrics.get_vehicle_metrics("v1")
        assert vm.edges_traversed == 1

    def test_record_updates_monetary_cost(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0, 5.0)
        assert metrics.get_total_monetary_cost() == 5.0

    def test_multiple_records_accumulate(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0, 5.0)
        metrics.record_edge_completion("v1", 200.0, 20.0, 10.0)
        assert metrics.get_total_distance() == 300.0
        assert metrics.get_total_travel_time() == 30.0
        assert metrics.get_total_monetary_cost() == 15.0

    def test_multiple_vehicles_tracked_separately(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        metrics.record_edge_completion("v2", 200.0, 20.0)
        assert metrics.get_vehicle_metrics("v1").distance_traveled == 100.0
        assert metrics.get_vehicle_metrics("v2").distance_traveled == 200.0
        assert metrics.get_total_distance() == 300.0

    def test_courier_metrics_extracted(self, metrics):
        metrics.record_edge_completion("courier1_car_0", 100.0, 10.0, 5.0)
        assert "courier1" in metrics._courier_metrics
        assert metrics._courier_metrics["courier1"].distance_traveled == 100.0

    def test_bus_not_in_courier_metrics(self, metrics):
        metrics.record_edge_completion("bus_1", 100.0, 10.0)
        assert "bus_1" not in metrics._courier_metrics
        assert len(metrics._courier_metrics) == 0

    def test_multiple_vehicles_same_courier_aggregated(self, metrics):
        metrics.record_edge_completion("courier1_car_0", 100.0, 10.0, 5.0)
        metrics.record_edge_completion("courier1_bike_1", 200.0, 20.0, 0.0)
        assert metrics._courier_metrics["courier1"].distance_traveled == 300.0


# -----------------------------------------------------------------------------
# MetricsCollector - Delivery Tracking
# -----------------------------------------------------------------------------

class TestMetricsCollectorDeliveryTracking:
    def test_record_delivery_assignment(self, metrics):
        metrics.record_delivery_assignment(5, 10)
        assert metrics._delivery_requests_assigned == 5
        assert metrics._delivery_requests_total == 10

    def test_get_delivery_assignment_rate(self, metrics):
        metrics.record_delivery_assignment(5, 10)
        assert metrics.get_delivery_assignment_rate() == 0.5

    def test_get_delivery_assignment_rate_zero_total(self, metrics):
        assert metrics.get_delivery_assignment_rate() == 0.0

    def test_record_delivery_completion(self, metrics):
        metrics.record_delivery_completion("v1", "courier1", 100.0)
        assert metrics._delivery_requests_delivered == 1

    def test_record_delivery_completion_tracks_time(self, metrics):
        metrics.record_delivery_completion("v1", "courier1", 100.0)
        vm = metrics.get_vehicle_metrics("v1")
        assert vm.delivery_times == [100.0]

    def test_record_delivery_completion_courier_tracking(self, metrics):
        metrics.record_delivery_completion("v1", "courier1", 100.0)
        assert metrics._courier_metrics["courier1"].delivery_times == [100.0]

    def test_get_delivery_completion_rate(self, metrics):
        metrics.record_delivery_assignment(10, 10)
        metrics.record_delivery_completion("v1", "courier1", 100.0)
        metrics.record_delivery_completion("v2", "courier1", 200.0)
        assert metrics.get_delivery_completion_rate() == 0.2  # 2/10

    def test_get_delivery_completion_rate_zero_assigned(self, metrics):
        assert metrics.get_delivery_completion_rate() == 0.0

    def test_get_average_delivery_time(self, metrics):
        metrics.record_delivery_completion("v1", "courier1", 100.0)
        metrics.record_delivery_completion("v1", "courier1", 200.0)
        assert metrics.get_average_delivery_time() == 150.0

    def test_get_average_delivery_time_empty(self, metrics):
        assert metrics.get_average_delivery_time() == 0.0


# -----------------------------------------------------------------------------
# MetricsCollector - Reset and Summary
# -----------------------------------------------------------------------------

class TestMetricsCollectorReset:
    def test_reset_clears_all_data(self, metrics):
        metrics.record_edge_completion("v1", 100.0, 10.0)
        metrics.record_delivery_assignment(5, 10)
        metrics.reset()
        assert len(metrics._vehicle_metrics) == 0
        assert metrics.get_total_distance() == 0.0
        assert metrics._delivery_requests_total == 0


class TestMetricsCollectorSummary:
    def test_get_summary_structure(self, metrics):
        metrics.record_edge_completion("v1", 1000.0, 100.0, 5.0)
        summary = metrics.get_summary()
        assert "total_distance" in summary
        assert "vehicles" in summary
        assert "couriers" in summary

    def test_get_summary_vehicle_data(self, metrics):
        metrics.record_edge_completion("v1", 1000.0, 100.0, 5.0)
        summary = metrics.get_summary()
        assert summary["vehicles"]["v1"]["distance"] == 1000.0


# -----------------------------------------------------------------------------
# VehicleTypeConfig
# -----------------------------------------------------------------------------

class TestVehicleTypeConfig:
    def test_fuel_consumption_calculation(self):
        config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=10.0,
            fuel_price_per_liter=1.50,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=20.0
        )
        assert config.calculate_fuel_consumption_l(100.0) == 10.0  # 100km / 10 km/L

    def test_fuel_consumption_infinite_efficiency(self):
        config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=float('inf'),
            fuel_price_per_liter=0.0,
            emission_factor_g_co2_per_l=0,
            is_clean_mode=True,
            labor_cost_per_hour=15.0
        )
        assert config.calculate_fuel_consumption_l(100.0) == 0.0

    def test_fuel_cost_calculation(self):
        config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=10.0,
            fuel_price_per_liter=1.50,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=20.0
        )
        # 100km needs 10L, at $1.50/L = $15
        assert config.calculate_fuel_cost(100.0) == 15.0

    def test_emissions_calculation(self):
        config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=10.0,
            fuel_price_per_liter=1.50,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=20.0
        )
        # 100km needs 10L, at 2300g/L = 23000g = 23kg
        assert config.calculate_emissions_kg(100.0) == 23.0

    def test_emission_intensity(self):
        config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=10.0,
            fuel_price_per_liter=1.50,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=20.0
        )
        # 2300g/L / 10km/L / 1000 = 0.23 kg/km = 230 g/km
        assert config.calculate_emission_intensity_kg_per_km() == 0.23

    def test_labor_cost_calculation(self):
        config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=10.0,
            fuel_price_per_liter=1.50,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=20.0
        )
        assert config.calculate_labor_cost(2.0) == 40.0  # 2 hours at $20/hr


# -----------------------------------------------------------------------------
# VehicleMetricsRow
# -----------------------------------------------------------------------------

class TestVehicleMetricsRow:
    def test_distance_km_property(self):
        row = VehicleMetricsRow("v1", 5000.0, 600.0, 2.50, 10, 3, 1200.0)
        assert row.distance_km == 5.0  # 5000m = 5km

    def test_travel_time_hours_property(self):
        row = VehicleMetricsRow("v1", 5000.0, 3600.0, 2.50, 10, 3, 1200.0)
        assert row.travel_time_hours == 1.0  # 3600s = 1hr

    def test_get_vehicle_type_courier_format(self):
        row = VehicleMetricsRow("courier1_car_0", 5000.0, 600.0, 2.50, 10, 3, 1200.0)
        assert row.get_vehicle_type() == "car"

    def test_get_vehicle_type_bus_format(self):
        row = VehicleMetricsRow("bus_1", 5000.0, 600.0, 2.50, 10, 0, 0.0)
        assert row.get_vehicle_type() == "bus"

    def test_get_vehicle_type_unknown(self):
        row = VehicleMetricsRow("unknown", 5000.0, 600.0, 2.50, 10, 0, 0.0)
        assert row.get_vehicle_type() == "unknown"


# -----------------------------------------------------------------------------
# CourierMetricsRow
# -----------------------------------------------------------------------------

class TestCourierMetricsRow:
    def test_distance_km_property(self):
        row = CourierMetricsRow("courier1", 5000.0, 600.0, 2.50, 10, 3, 1200.0)
        assert row.distance_km == 5.0

    def test_travel_time_hours_property(self):
        row = CourierMetricsRow("courier1", 5000.0, 3600.0, 2.50, 10, 3, 1200.0)
        assert row.travel_time_hours == 1.0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Initialization
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsInit:
    def test_initialization(self, sample_vehicle_configs, sample_vehicle_data,
                           sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert psm.vehicle_configs == sample_vehicle_configs
        assert psm.vehicle_data == sample_vehicle_data
        assert len(psm._vehicles_by_type) > 0

    def test_vehicles_grouped_by_type(self, sample_vehicle_configs, sample_vehicle_data,
                                     sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert "car" in psm._vehicles_by_type
        assert "bike" in psm._vehicles_by_type
        assert len(psm._vehicles_by_type["car"]) == 2


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Aggregate Metrics
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsAggregate:
    def test_total_distance_km(self, sample_vehicle_configs, sample_vehicle_data,
                              sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert psm.total_distance_km() == 20.0  # Sum of all distances in km

    def test_total_travel_time_hours(self, sample_vehicle_configs, sample_vehicle_data,
                                    sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        expected = (600 + 400 + 900 + 1200) / 3600  # Convert seconds to hours
        assert psm.total_travel_time_hours() == expected

    def test_total_deliveries(self, sample_vehicle_configs, sample_vehicle_data,
                             sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert psm.total_deliveries() == 10  # 3 + 2 + 5 + 0

    def test_total_congestion_cost(self, sample_vehicle_configs, sample_vehicle_data,
                                  sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert psm.total_congestion_cost() == 9.0  # 2.50 + 1.50 + 0.0 + 5.0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Fuel Metrics
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsFuel:
    def test_total_fuel_consumption(self, sample_vehicle_configs, sample_vehicle_data,
                                   sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        # cars: 8km / 15km/L = 0.533L, bikes: 2km / inf = 0L, bus: 10km / 5km/L = 2L
        expected = (8.0/15.0) + 0.0 + 2.0
        assert abs(psm.total_fuel_consumption_l() - expected) < 0.01

    def test_fuel_consumption_by_type(self, sample_vehicle_configs, sample_vehicle_data,
                                     sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        by_type = psm.fuel_consumption_by_type_l()
        assert "car" in by_type
        assert "bike" in by_type
        assert by_type["bike"] == 0.0

    def test_fleet_fuel_efficiency(self, sample_vehicle_configs, sample_vehicle_data,
                                  sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        # Total distance: 20km, total fuel: ~2.53L
        efficiency = psm.fleet_fuel_efficiency_km_per_l()
        assert efficiency > 0

    def test_total_fuel_cost(self, sample_vehicle_configs, sample_vehicle_data,
                            sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        cost = psm.total_fuel_cost()
        assert cost > 0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Emission Metrics
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsEmissions:
    def test_total_emissions(self, sample_vehicle_configs, sample_vehicle_data,
                            sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        emissions = psm.total_emissions_kg_co2()
        assert emissions > 0

    def test_bike_emissions_zero(self, sample_vehicle_configs, sample_vehicle_data,
                                sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        by_type = psm.emissions_by_type_kg()
        assert by_type["bike"] == 0.0

    def test_fleet_emission_factor(self, sample_vehicle_configs, sample_vehicle_data,
                                  sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        factor = psm.fleet_emission_factor_g_per_km()
        assert factor > 0

    def test_emissions_per_delivery(self, sample_vehicle_configs, sample_vehicle_data,
                                   sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        epd = psm.emissions_per_delivery_kg()
        assert epd > 0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Cost Metrics
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsCosts:
    def test_total_labor_cost(self, sample_vehicle_configs, sample_vehicle_data,
                             sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        labor = psm.total_labor_cost()
        assert labor > 0

    def test_total_operational_cost(self, sample_vehicle_configs, sample_vehicle_data,
                                   sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        total = psm.total_operational_cost()
        expected = psm.total_fuel_cost() + psm.total_labor_cost() + psm.total_congestion_cost()
        assert abs(total - expected) < 0.01

    def test_cost_breakdown(self, sample_vehicle_configs, sample_vehicle_data,
                           sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        breakdown = psm.cost_breakdown()
        assert "fuel" in breakdown
        assert "labor" in breakdown
        assert "congestion" in breakdown
        assert "total" in breakdown

    def test_cost_per_delivery(self, sample_vehicle_configs, sample_vehicle_data,
                              sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        cpd = psm.cost_per_delivery()
        assert cpd > 0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Mode Share
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsModeShare:
    def test_clean_mode_share(self, sample_vehicle_configs, sample_vehicle_data,
                             sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        # 5 deliveries by bike (clean) out of 10 total
        assert psm.clean_mode_share() == 0.5

    def test_distance_by_type(self, sample_vehicle_configs, sample_vehicle_data,
                             sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        by_type = psm.distance_by_type_km()
        assert by_type["car"] == 8.0  # 5km + 3km
        assert by_type["bike"] == 2.0
        assert by_type["bus"] == 10.0

    def test_deliveries_by_type(self, sample_vehicle_configs, sample_vehicle_data,
                               sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        by_type = psm.deliveries_by_type()
        assert by_type["car"] == 5  # 3 + 2
        assert by_type["bike"] == 5
        assert by_type["bus"] == 0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - Edge Cases
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsEdgeCases:
    def test_zero_distance_fuel_efficiency(self, sample_vehicle_configs):
        empty_data = []
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            empty_data,
            [],
            {}
        )
        assert psm.fleet_fuel_efficiency_km_per_l() == float('inf')

    def test_zero_distance_emission_factor(self, sample_vehicle_configs):
        empty_data = []
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            empty_data,
            [],
            {}
        )
        assert psm.fleet_emission_factor_g_per_km() == 0.0

    def test_zero_deliveries_cost_per_delivery(self, sample_vehicle_configs, sample_vehicle_data,
                                              sample_courier_data, sample_totals_data):
        # Modify data to have zero deliveries
        for v in sample_vehicle_data:
            v.deliveries_count = 0
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert psm.cost_per_delivery() == 0.0

    def test_zero_deliveries_clean_mode_share(self, sample_vehicle_configs, sample_vehicle_data,
                                             sample_courier_data, sample_totals_data):
        for v in sample_vehicle_data:
            v.deliveries_count = 0
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        assert psm.clean_mode_share() == 0.0


# -----------------------------------------------------------------------------
# PostSimulationMetrics - CSV Output
# -----------------------------------------------------------------------------

class TestPostSimulationMetricsCSVOutput:
    def test_dump_to_csv_creates_file(self, sample_vehicle_configs, sample_vehicle_data,
                                     sample_courier_data, sample_totals_data, tmp_path):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        output_file = tmp_path / "business_metrics.csv"
        psm.dump_to_csv(str(output_file))
        assert output_file.exists()

    def test_dump_to_csv_content(self, sample_vehicle_configs, sample_vehicle_data,
                                sample_courier_data, sample_totals_data, tmp_path):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        output_file = tmp_path / "business_metrics.csv"
        psm.dump_to_csv(str(output_file))
        
        with open(output_file, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) > 0
        assert rows[0] == ["metric", "value", "unit"]

    def test_get_summary_structure(self, sample_vehicle_configs, sample_vehicle_data,
                                  sample_courier_data, sample_totals_data):
        psm = PostSimulationMetrics(
            sample_vehicle_configs,
            sample_vehicle_data,
            sample_courier_data,
            sample_totals_data
        )
        summary = psm.get_summary()
        assert "distance" in summary
        assert "fuel" in summary
        assert "emissions" in summary
        assert "costs" in summary
        assert "mode_share" in summary
        assert "time" in summary
