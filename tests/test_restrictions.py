import pytest

from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge


class TestProhibitEdge:
    def test_attributes(self):
        r = ProhibitEdge(edge_id=5, vehicle_type="car")
        assert r.edge_id == 5
        assert r.vehicle_type == "car"

    def test_vehicle_type_defaults_to_none(self):
        r = ProhibitEdge(edge_id=3)
        assert r.vehicle_type is None

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
