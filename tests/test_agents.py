import pytest
from parcel_delivery_two.agents.transport_vehicle import TransportVehicle
from parcel_delivery_two.agents.courier_vehicle import CourierVehicle
from parcel_delivery_two.agents.bus import Bus


# ---------------------------------------------------------------------------
# TransportVehicle (base class)
# ---------------------------------------------------------------------------

class TestTransportVehicle:
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


# ---------------------------------------------------------------------------
# CourierVehicle
# ---------------------------------------------------------------------------

class TestCourierVehicle:
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


# ---------------------------------------------------------------------------
# Bus
# ---------------------------------------------------------------------------

class TestBus:
    def test_attributes(self):
        b = Bus("bus_1", itinerary=[5, 10, 15], travel_time_factor=2.0)
        assert b.entity_id == "bus_1"
        assert b.itinerary == [5, 10, 15]
        assert b.travel_time_factor == 2.0

    def test_default_travel_time_factor(self):
        b = Bus("bus_1", itinerary=[5, 10])
        assert b.travel_time_factor == 2.0
