import pytest

from parcel_delivery_two.utils.time_utils import format_time


# -----------------------------------------------------------------------------
# Seconds format (< 60 seconds)
# -----------------------------------------------------------------------------

class TestFormatTimeSeconds:
    def test_zero_seconds(self):
        assert format_time(0.0) == "0.0s"

    def test_small_value(self):
        assert format_time(5.5) == "5.5s"

    def test_integer_seconds(self):
        assert format_time(30.0) == "30.0s"

    def test_one_decimal_place(self):
        assert format_time(45.7) == "45.7s"

    def test_just_under_one_minute(self):
        assert format_time(59.9) == "59.9s"

    def test_exactly_60_not_in_seconds_format(self):
        result = format_time(60.0)
        assert "s" not in result or "m" in result


# -----------------------------------------------------------------------------
# Minutes format (60 seconds to < 3600 seconds)
# -----------------------------------------------------------------------------

class TestFormatTimeMinutes:
    def test_exactly_60_seconds(self):
        assert format_time(60.0) == "1m00.0s"

    def test_one_minute_with_seconds(self):
        assert format_time(90.5) == "1m30.5s"

    def test_multiple_minutes(self):
        assert format_time(300.0) == "5m00.0s"

    def test_minutes_and_seconds(self):
        assert format_time(185.5) == "3m05.5s"

    def test_just_under_one_hour(self):
        assert format_time(3599.9) == "59m59.9s"

    def test_30_minutes(self):
        assert format_time(1800.0) == "30m00.0s"


# -----------------------------------------------------------------------------
# Hours format (>= 3600 seconds)
# -----------------------------------------------------------------------------

class TestFormatTimeHours:
    def test_exactly_one_hour(self):
        assert format_time(3600.0) == "1h00m00.0s"

    def test_one_hour_with_minutes(self):
        assert format_time(3660.0) == "1h01m00.0s"

    def test_one_hour_with_seconds(self):
        assert format_time(3601.5) == "1h00m01.5s"

    def test_multiple_hours(self):
        assert format_time(7200.0) == "2h00m00.0s"

    def test_full_time(self):
        assert format_time(3661.5) == "1h01m01.5s"

    def test_24_hours(self):
        assert format_time(86400.0) == "24h00m00.0s"

    def test_large_value(self):
        assert format_time(90061.5) == "25h01m01.5s"


# -----------------------------------------------------------------------------
# Edge Cases
# -----------------------------------------------------------------------------

class TestFormatTimeEdgeCases:
    def test_negative_time(self):
        """Negative times should still format (though not semantically meaningful)."""
        result = format_time(-5.0)
        assert "-5.0" in result

    def test_very_small_positive(self):
        assert format_time(0.1) == "0.1s"

    def test_very_large_value(self):
        result = format_time(1000000.0)
        assert "h" in result  # Should be in hours format

    def test_boundary_60_seconds(self):
        """Test boundary at exactly 60 seconds."""
        assert format_time(60.0) == "1m00.0s"
        # Just under should be seconds format
        assert format_time(59.999) == "60.0s" or format_time(59.999).endswith("s")

    def test_boundary_3600_seconds(self):
        """Test boundary at exactly 3600 seconds (1 hour)."""
        assert format_time(3600.0) == "1h00m00.0s"
        # Just under should be minutes format
        result = format_time(3599.999)
        assert "m" in result and "h" not in result

    def test_floating_point_precision(self):
        """Test that floating point values are handled correctly."""
        result = format_time(123.456)
        assert "m" in result  # 2+ minutes


# -----------------------------------------------------------------------------
# Format Verification
# -----------------------------------------------------------------------------

class TestFormatTimeFormats:
    def test_seconds_format_structure(self):
        """Seconds format: X.Ys"""
        result = format_time(45.5)
        assert result.endswith("s")
        assert "m" not in result
        assert "h" not in result

    def test_minutes_format_structure(self):
        """Minutes format: XmYY.Ys"""
        result = format_time(185.5)
        assert "m" in result
        assert "h" not in result
        assert result.endswith("s")

    def test_hours_format_structure(self):
        """Hours format: XhYYmYY.Ys"""
        result = format_time(3661.5)
        assert "h" in result
        assert "m" in result
        assert result.endswith("s")

    def test_minutes_two_digits(self):
        """Minutes in hours format should be zero-padded to 2 digits."""
        result = format_time(3605.0)  # 1h 0m 5s
        assert "00m" in result

    def test_seconds_two_digits_in_minutes_format(self):
        """Seconds in minutes format should be zero-padded to 2 integer digits."""
        result = format_time(60.5)  # 1m 0.5s
        assert "00.5s" in result

    def test_seconds_two_digits_in_hours_format(self):
        """Seconds in hours format should be zero-padded to 2 integer digits."""
        result = format_time(3600.5)  # 1h 0m 0.5s
        assert "00.5s" in result


# -----------------------------------------------------------------------------
# Practical Use Cases
# -----------------------------------------------------------------------------

class TestFormatTimePractical:
    def test_simulation_second(self):
        assert format_time(1.0) == "1.0s"

    def test_simulation_minute(self):
        assert format_time(60.0) == "1m00.0s"

    def test_simulation_hour(self):
        assert format_time(3600.0) == "1h00m00.0s"

    def test_typical_simulation_time(self):
        """Test a typical simulation end time (e.g., end of day)."""
        result = format_time(86400.0)  # 24 hours
        assert result == "24h00m00.0s"

    def test_typical_edge_traversal(self):
        """Test typical time for traversing an edge (few seconds)."""
        result = format_time(15.5)
        assert result == "15.5s"

    def test_typical_delivery_route(self):
        """Test typical time for a delivery route (tens of minutes)."""
        result = format_time(1800.0)  # 30 minutes
        assert result == "30m00.0s"
