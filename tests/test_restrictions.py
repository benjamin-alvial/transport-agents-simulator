import pytest

from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing


class TestProhibitEdgeAttributes:
    def test_attributes(self):
        r = ProhibitEdge(edge_id=5, vehicle_type="car")
        assert r.edge_id == 5
        assert r.vehicle_type == "car"
        assert r.time_window is None

    def test_vehicle_type_defaults_to_none(self):
        r = ProhibitEdge(edge_id=3)
        assert r.vehicle_type is None

    def test_time_window_defaults_to_none(self):
        r = ProhibitEdge(edge_id=1)
        assert r.time_window is None

    def test_time_window_set(self):
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 7200])
        assert r.time_window == [3600, 7200]


class TestProhibitEdgeBlocks:
    """Tests for the blocks() method."""

    def test_blocks_matching_vehicle_type(self):
        r = ProhibitEdge(edge_id=1, vehicle_type="car")
        assert r.blocks("car") is True

    def test_does_not_block_different_vehicle_type(self):
        r = ProhibitEdge(edge_id=1, vehicle_type="car")
        assert r.blocks("bike") is False

    def test_none_vehicle_type_blocks_all(self):
        r = ProhibitEdge(edge_id=1, vehicle_type=None)
        assert r.blocks("car") is True
        assert r.blocks("bike") is True
        assert r.blocks("truck") is True

    def test_blocks_without_time_window(self):
        """When no time window, blocks matching vehicle type regardless of time."""
        r = ProhibitEdge(edge_id=1, vehicle_type="car")
        assert r.blocks("car", time=0) is True
        assert r.blocks("car", time=3600) is True
        assert r.blocks("car", time=86400) is True
        assert r.blocks("car", time=None) is True

    def test_blocks_within_time_window(self):
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 7200])
        assert r.blocks("car", time=3600) is True  # At start
        assert r.blocks("car", time=5400) is True  # Middle
        assert r.blocks("car", time=7200) is True  # At end

    def test_does_not_block_before_time_window(self):
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 7200])
        assert r.blocks("car", time=0) is False
        assert r.blocks("car", time=3599) is False

    def test_does_not_block_after_time_window(self):
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 7200])
        assert r.blocks("car", time=7201) is False
        assert r.blocks("car", time=86400) is False

    def test_no_time_specified_with_time_window_returns_false(self):
        """If time_window is set but time is None, restriction is not active."""
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 7200])
        assert r.blocks("car", time=None) is False

    def test_wrong_vehicle_type_ignores_time_window(self):
        """If vehicle type doesn't match, time window shouldn't matter."""
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 7200])
        assert r.blocks("bike", time=5400) is False


class TestProhibitEdgeEdgeCases:
    """Edge cases for ProhibitEdge."""

    def test_does_not_block_non_matching_vehicle_with_none_restriction(self):
        """When vehicle_type is None, all vehicles are blocked."""
        r = ProhibitEdge(edge_id=1, vehicle_type=None)
        assert r.blocks("any_vehicle") is True
        assert r.blocks("car", time=0) is True
        assert r.blocks("bike", time=100000) is True

    def test_empty_time_window_list_raises(self):
        """Empty time window list raises ValueError."""
        with pytest.raises(ValueError, match="time_window must be a list of exactly 2 elements"):
            ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[])

    def test_single_element_time_window_raises(self):
        """Single element time window raises ValueError."""
        with pytest.raises(ValueError, match="time_window must be a list of exactly 2 elements"):
            ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600])

    def test_reversed_time_window_raises(self):
        """Reversed time window [end, start] raises ValueError."""
        with pytest.raises(ValueError, match="time_window end .* must be >= start"):
            ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[7200, 3600])

    def test_equal_start_end_time_window_allowed(self):
        """Time window with start == end should be allowed (zero-duration window)."""
        r = ProhibitEdge(edge_id=1, vehicle_type="car", time_window=[3600, 3600])
        assert r.time_window == [3600, 3600]
        assert r.blocks("car", time=3600) is True


# ---------------------------------------------------------------------------
# CongestionPricing
# ---------------------------------------------------------------------------

class TestCongestionPricingAttributes:
    def test_attributes(self):
        cp = CongestionPricing(edge_id=5, cost=2.50, vehicle_type="car")
        assert cp.edge_id == 5
        assert cp.cost == 2.50
        assert cp.vehicle_type == "car"
        assert cp.time_window is None

    def test_vehicle_type_defaults_to_none(self):
        cp = CongestionPricing(edge_id=1, cost=1.00)
        assert cp.vehicle_type is None

    def test_time_window_defaults_to_none(self):
        cp = CongestionPricing(edge_id=1, cost=1.00)
        assert cp.time_window is None

    def test_time_window_set(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, time_window=[3600, 7200])
        assert cp.time_window == [3600, 7200]


class TestCongestionPricingApplies:
    """Tests for the applies() method."""

    def test_applies_to_matching_vehicle_type(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car")
        assert cp.applies("car") is True

    def test_does_not_apply_to_different_vehicle_type(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car")
        assert cp.applies("bike") is False

    def test_none_vehicle_type_applies_to_all(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type=None)
        assert cp.applies("car") is True
        assert cp.applies("bike") is True
        assert cp.applies("truck") is True

    def test_applies_without_time_window(self):
        """When no time window, applies to matching vehicle type regardless of time."""
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car")
        assert cp.applies("car", time=0) is True
        assert cp.applies("car", time=3600) is True
        assert cp.applies("car", time=86400) is True
        assert cp.applies("car", time=None) is True

    def test_applies_within_time_window(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600, 7200])
        assert cp.applies("car", time=3600) is True  # At start
        assert cp.applies("car", time=5400) is True  # Middle
        assert cp.applies("car", time=7200) is True  # At end

    def test_does_not_apply_before_time_window(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600, 7200])
        assert cp.applies("car", time=0) is False
        assert cp.applies("car", time=3599) is False

    def test_does_not_apply_after_time_window(self):
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600, 7200])
        assert cp.applies("car", time=7201) is False
        assert cp.applies("car", time=86400) is False

    def test_no_time_specified_with_time_window_returns_false(self):
        """If time_window is set but time is None, should return False."""
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600, 7200])
        assert cp.applies("car", time=None) is False

    def test_wrong_vehicle_type_ignores_time_window(self):
        """If vehicle type doesn't match, time window shouldn't matter."""
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600, 7200])
        assert cp.applies("bike", time=5400) is False


class TestCongestionPricingGetCost:
    """Tests for the get_cost() method."""

    def test_get_cost_when_applies(self):
        cp = CongestionPricing(edge_id=1, cost=2.50, vehicle_type="car")
        assert cp.get_cost("car", time=3600) == 2.50

    def test_get_cost_when_does_not_apply_wrong_type(self):
        cp = CongestionPricing(edge_id=1, cost=2.50, vehicle_type="car")
        assert cp.get_cost("bike", time=3600) == 0.0

    def test_get_cost_when_does_not_apply_outside_time_window(self):
        cp = CongestionPricing(edge_id=1, cost=2.50, vehicle_type="car", time_window=[3600, 7200])
        assert cp.get_cost("car", time=0) == 0.0
        assert cp.get_cost("car", time=7201) == 0.0

    def test_get_cost_zero_cost(self):
        cp = CongestionPricing(edge_id=1, cost=0.00, vehicle_type="car")
        assert cp.get_cost("car", time=3600) == 0.0

    def test_get_cost_all_vehicles(self):
        cp = CongestionPricing(edge_id=1, cost=5.00, vehicle_type=None)
        assert cp.get_cost("car", time=3600) == 5.00
        assert cp.get_cost("bike", time=3600) == 5.00
        assert cp.get_cost("truck", time=3600) == 5.00


class TestCongestionPricingEdgeCases:
    """Edge cases for CongestionPricing."""

    def test_negative_cost(self):
        """Negative cost (subsidy) should be allowed."""
        cp = CongestionPricing(edge_id=1, cost=-1.00, vehicle_type="car")
        assert cp.get_cost("car") == -1.00

    def test_empty_time_window_list_raises(self):
        """Empty time window list raises ValueError."""
        with pytest.raises(ValueError, match="time_window must be a list of exactly 2 elements"):
            CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[])

    def test_single_element_time_window_raises(self):
        """Single element time window raises ValueError."""
        with pytest.raises(ValueError, match="time_window must be a list of exactly 2 elements"):
            CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600])

    def test_reversed_time_window_raises(self):
        """Reversed time window [end, start] raises ValueError."""
        with pytest.raises(ValueError, match="time_window end .* must be >= start"):
            CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[7200, 3600])

    def test_equal_start_end_time_window_allowed(self):
        """Time window with start == end should be allowed (zero-duration window)."""
        cp = CongestionPricing(edge_id=1, cost=1.00, vehicle_type="car", time_window=[3600, 3600])
        assert cp.time_window == [3600, 3600]
        assert cp.applies("car", time=3600) is True
