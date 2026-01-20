import unittest
from unittest.mock import Mock

from parcel_delivery.models.bid import Bid
from parcel_delivery.models.parcel import Parcel
from parcel_delivery.models.stop import Stop


class TestParcel(unittest.TestCase):
    """Tests for the Parcel class"""

    def test_parcel_initialization(self):
        """Test parcel initializes with correct values"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        self.assertEqual(parcel.contents, "laptop")
        self.assertEqual(parcel.origin, 50)
        self.assertEqual(parcel.destination, 100)
        self.assertEqual(parcel.weight, 5.0)
        self.assertEqual(parcel.fare, 15.0)
        self.assertEqual(parcel.state, "WAITING_PICK_UP")

    def test_parcel_default_state(self):
        """Test parcel defaults to WAITING_PICK_UP state"""
        parcel = Parcel("book", 10, 20, 1.0, 5.0)
        self.assertEqual(parcel.state, "WAITING_PICK_UP")

    def test_parcel_state_can_be_changed(self):
        """Test parcel state can be modified"""
        parcel = Parcel("phone", 30, 60, 0.5, 8.0)

        parcel.state = "BEING_DELIVERED"
        self.assertEqual(parcel.state, "BEING_DELIVERED")

        parcel.state = "DELIVERED"
        self.assertEqual(parcel.state, "DELIVERED")

    def test_parcel_with_various_contents(self):
        """Test parcels can have different content descriptions"""
        parcel1 = Parcel("documents", 0, 100, 0.1, 5.0)
        parcel2 = Parcel("furniture", 50, 200, 50.0, 100.0)
        parcel3 = Parcel("gift box", 10, 30, 2.0, 10.0)

        self.assertEqual(parcel1.contents, "documents")
        self.assertEqual(parcel2.contents, "furniture")
        self.assertEqual(parcel3.contents, "gift box")

    def test_parcel_with_zero_weight(self):
        """Test parcel can have zero weight (edge case)"""
        parcel = Parcel("letter", 10, 20, 0.0, 2.0)
        self.assertEqual(parcel.weight, 0.0)

    def test_parcel_with_large_weight(self):
        """Test parcel can have large weight"""
        parcel = Parcel("machinery", 0, 500, 1000.0, 500.0)
        self.assertEqual(parcel.weight, 1000.0)

    def test_parcel_origin_destination_same(self):
        """Test parcel can have same origin and destination (edge case)"""
        parcel = Parcel("local", 50, 50, 1.0, 5.0)
        self.assertEqual(parcel.origin, 50)
        self.assertEqual(parcel.destination, 50)

    def test_parcel_negative_locations(self):
        """Test parcel can have negative location values"""
        parcel = Parcel("item", -10, -5, 1.0, 5.0)
        self.assertEqual(parcel.origin, -10)
        self.assertEqual(parcel.destination, -5)

    def test_parcel_repr(self):
        """Test parcel string representation"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        repr_str = repr(parcel)

        self.assertIn("laptop", repr_str)
        self.assertIn("origin=50", repr_str)
        self.assertIn("destination=100", repr_str)
        self.assertIn("weight=5.0", repr_str)
        self.assertIn("fare=15.0", repr_str)
        self.assertIn("state=WAITING_PICK_UP", repr_str)

    def test_parcel_repr_with_different_state(self):
        """Test parcel repr reflects current state"""
        parcel = Parcel("book", 10, 20, 1.0, 5.0)
        parcel.state = "DELIVERED"

        repr_str = repr(parcel)
        self.assertIn("state=DELIVERED", repr_str)

    def test_parcel_attributes_are_mutable(self):
        """Test parcel attributes can be modified after creation"""
        parcel = Parcel("item", 0, 100, 1.0, 5.0)

        # Modify attributes
        parcel.contents = "new_item"
        parcel.weight = 2.0
        parcel.fare = 10.0

        self.assertEqual(parcel.contents, "new_item")
        self.assertEqual(parcel.weight, 2.0)
        self.assertEqual(parcel.fare, 10.0)

    def test_parcel_float_precision(self):
        """Test parcel handles float precision correctly"""
        parcel = Parcel("precise", 0, 100, 3.14159, 9.99)
        self.assertAlmostEqual(parcel.weight, 3.14159, places=5)
        self.assertAlmostEqual(parcel.fare, 9.99, places=2)

    def test_multiple_parcels_independence(self):
        """Test multiple parcels are independent objects"""
        parcel1 = Parcel("item1", 0, 100, 1.0, 5.0)
        parcel2 = Parcel("item2", 50, 150, 2.0, 10.0)

        parcel1.state = "DELIVERED"

        # parcel2 should not be affected
        self.assertEqual(parcel1.state, "DELIVERED")
        self.assertEqual(parcel2.state, "WAITING_PICK_UP")


class TestStop(unittest.TestCase):
    """Tests for the Stop class"""

    def test_stop_initialization(self):
        """Test stop initializes with correct values"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        stop = Stop(50, "WAITING_PICK_UP", parcel)

        self.assertEqual(stop.location, 50)
        self.assertEqual(stop.stop_type, "WAITING_PICK_UP")
        self.assertEqual(stop.parcel, parcel)

    def test_stop_pickup_type(self):
        """Test stop with WAITING_PICK_UP type"""
        parcel = Parcel("book", 10, 20, 1.0, 5.0)
        stop = Stop(10, "WAITING_PICK_UP", parcel)

        self.assertEqual(stop.stop_type, "WAITING_PICK_UP")
        self.assertEqual(stop.location, parcel.origin)

    def test_stop_delivery_type(self):
        """Test stop with BEING_DELIVERED type"""
        parcel = Parcel("book", 10, 20, 1.0, 5.0)
        stop = Stop(20, "BEING_DELIVERED", parcel)

        self.assertEqual(stop.stop_type, "BEING_DELIVERED")
        self.assertEqual(stop.location, parcel.destination)

    def test_stop_location_matches_parcel_origin(self):
        """Test pickup stop location matches parcel origin"""
        parcel = Parcel("item", 75, 150, 2.0, 8.0)
        stop = Stop(parcel.origin, "WAITING_PICK_UP", parcel)

        self.assertEqual(stop.location, 75)
        self.assertEqual(stop.location, parcel.origin)

    def test_stop_location_matches_parcel_destination(self):
        """Test delivery stop location matches parcel destination"""
        parcel = Parcel("item", 75, 150, 2.0, 8.0)
        stop = Stop(parcel.destination, "BEING_DELIVERED", parcel)

        self.assertEqual(stop.location, 150)
        self.assertEqual(stop.location, parcel.destination)

    def test_stop_with_negative_location(self):
        """Test stop can have negative location"""
        parcel = Parcel("item", -50, 100, 1.0, 5.0)
        stop = Stop(-50, "WAITING_PICK_UP", parcel)

        self.assertEqual(stop.location, -50)

    def test_stop_references_correct_parcel(self):
        """Test stop maintains reference to its parcel"""
        parcel1 = Parcel("item1", 0, 100, 1.0, 5.0)
        parcel2 = Parcel("item2", 50, 150, 2.0, 10.0)

        stop1 = Stop(0, "WAITING_PICK_UP", parcel1)
        stop2 = Stop(50, "WAITING_PICK_UP", parcel2)

        self.assertEqual(stop1.parcel, parcel1)
        self.assertEqual(stop2.parcel, parcel2)
        self.assertNotEqual(stop1.parcel, stop2.parcel)

    def test_stop_parcel_reference_is_same_object(self):
        """Test stop holds reference to same parcel object"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        stop = Stop(50, "WAITING_PICK_UP", parcel)

        # Modify parcel through stop reference
        stop.parcel.state = "BEING_DELIVERED"

        # Original parcel should be affected
        self.assertEqual(parcel.state, "BEING_DELIVERED")

    def test_stop_attributes_are_mutable(self):
        """Test stop attributes can be modified"""
        parcel = Parcel("item", 0, 100, 1.0, 5.0)
        stop = Stop(0, "WAITING_PICK_UP", parcel)

        # Modify stop attributes
        stop.location = 25
        stop.stop_type = "CUSTOM_TYPE"

        self.assertEqual(stop.location, 25)
        self.assertEqual(stop.stop_type, "CUSTOM_TYPE")

    def test_multiple_stops_for_same_parcel(self):
        """Test creating multiple stops for the same parcel"""
        parcel = Parcel("item", 50, 100, 1.0, 5.0)

        pickup_stop = Stop(parcel.origin, "WAITING_PICK_UP", parcel)
        delivery_stop = Stop(parcel.destination, "BEING_DELIVERED", parcel)

        self.assertEqual(pickup_stop.parcel, delivery_stop.parcel)
        self.assertEqual(pickup_stop.location, 50)
        self.assertEqual(delivery_stop.location, 100)
        self.assertNotEqual(pickup_stop.stop_type, delivery_stop.stop_type)

    def test_stop_with_zero_location(self):
        """Test stop at location zero"""
        parcel = Parcel("item", 0, 100, 1.0, 5.0)
        stop = Stop(0, "WAITING_PICK_UP", parcel)

        self.assertEqual(stop.location, 0)


class TestBid(unittest.TestCase):
    """Tests for the Bid class"""

    def test_bid_initialization(self):
        """Test bid initializes with correct values"""
        courier = Mock()
        auction = Mock()

        bid = Bid(courier, auction, 10.0)

        self.assertEqual(bid.courier, courier)
        self.assertEqual(bid.auction, auction)
        self.assertEqual(bid.value, 10.0)

    def test_bid_with_different_values(self):
        """Test bids can have different values"""
        courier = Mock()
        auction = Mock()

        bid1 = Bid(courier, auction, 5.0)
        bid2 = Bid(courier, auction, 15.0)
        bid3 = Bid(courier, auction, 1.0)

        self.assertEqual(bid1.value, 5.0)
        self.assertEqual(bid2.value, 15.0)
        self.assertEqual(bid3.value, 1.0)

    def test_bid_with_zero_value(self):
        """Test bid can have zero value (free delivery)"""
        courier = Mock()
        auction = Mock()

        bid = Bid(courier, auction, 0.0)
        self.assertEqual(bid.value, 0.0)

    def test_bid_with_negative_value(self):
        """Test bid can technically have negative value (edge case)"""
        courier = Mock()
        auction = Mock()

        bid = Bid(courier, auction, -5.0)
        self.assertEqual(bid.value, -5.0)

    def test_bid_maintains_courier_reference(self):
        """Test bid maintains reference to courier"""
        courier1 = Mock()
        courier1.agent_id = "courier1"
        courier2 = Mock()
        courier2.agent_id = "courier2"
        auction = Mock()

        bid1 = Bid(courier1, auction, 10.0)
        bid2 = Bid(courier2, auction, 8.0)

        self.assertEqual(bid1.courier, courier1)
        self.assertEqual(bid2.courier, courier2)
        self.assertNotEqual(bid1.courier, bid2.courier)

    def test_bid_maintains_auction_reference(self):
        """Test bid maintains reference to auction"""
        courier = Mock()
        auction1 = Mock()
        auction1.agent_id = "auction1"
        auction2 = Mock()
        auction2.agent_id = "auction2"

        bid1 = Bid(courier, auction1, 10.0)
        bid2 = Bid(courier, auction2, 10.0)

        self.assertEqual(bid1.auction, auction1)
        self.assertEqual(bid2.auction, auction2)
        self.assertNotEqual(bid1.auction, bid2.auction)

    def test_bid_value_is_mutable(self):
        """Test bid value can be modified after creation"""
        courier = Mock()
        auction = Mock()

        bid = Bid(courier, auction, 10.0)
        bid.value = 5.0

        self.assertEqual(bid.value, 5.0)

    def test_bid_courier_reference_is_same_object(self):
        """Test bid holds reference to same courier object"""
        courier = Mock()
        courier.position = 0
        auction = Mock()

        bid = Bid(courier, auction, 10.0)

        # Modify courier through bid reference
        bid.courier.position = 100

        # Original courier should be affected
        self.assertEqual(courier.position, 100)

    def test_bid_auction_reference_is_same_object(self):
        """Test bid holds reference to same auction object"""
        courier = Mock()
        auction = Mock()
        auction.duration = 20

        bid = Bid(courier, auction, 10.0)

        # Modify auction through bid reference
        bid.auction.duration = 30

        # Original auction should be affected
        self.assertEqual(auction.duration, 30)

    def test_multiple_bids_from_same_courier(self):
        """Test same courier can create multiple bids"""
        courier = Mock()
        courier.agent_id = "courier1"
        auction1 = Mock()
        auction2 = Mock()

        bid1 = Bid(courier, auction1, 10.0)
        bid2 = Bid(courier, auction2, 15.0)

        self.assertEqual(bid1.courier, bid2.courier)
        self.assertNotEqual(bid1.auction, bid2.auction)
        self.assertNotEqual(bid1.value, bid2.value)

    def test_multiple_bids_on_same_auction(self):
        """Test multiple couriers can bid on same auction"""
        courier1 = Mock()
        courier2 = Mock()
        auction = Mock()

        bid1 = Bid(courier1, auction, 10.0)
        bid2 = Bid(courier2, auction, 8.0)

        self.assertEqual(bid1.auction, bid2.auction)
        self.assertNotEqual(bid1.courier, bid2.courier)

    def test_bid_float_precision(self):
        """Test bid handles float precision correctly"""
        courier = Mock()
        auction = Mock()

        bid = Bid(courier, auction, 7.99)
        self.assertAlmostEqual(bid.value, 7.99, places=2)

    def test_bid_with_large_value(self):
        """Test bid with very large value"""
        courier = Mock()
        auction = Mock()

        bid = Bid(courier, auction, 999999.99)
        self.assertEqual(bid.value, 999999.99)


class TestModelIntegration(unittest.TestCase):
    """Integration tests for model classes working together"""

    def test_parcel_stop_workflow(self):
        """Test parcel and stop working together in typical workflow"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        # Create pickup stop
        pickup_stop = Stop(parcel.origin, "WAITING_PICK_UP", parcel)
        self.assertEqual(pickup_stop.location, 50)
        self.assertEqual(pickup_stop.parcel.state, "WAITING_PICK_UP")

        # Simulate pickup
        parcel.state = "BEING_DELIVERED"

        # Create delivery stop
        delivery_stop = Stop(parcel.destination, "BEING_DELIVERED", parcel)
        self.assertEqual(delivery_stop.location, 100)
        self.assertEqual(delivery_stop.parcel.state, "BEING_DELIVERED")

    def test_bid_comparison_for_winner_selection(self):
        """Test comparing bids to find lowest value (winner)"""
        courier1 = Mock()
        courier1.agent_id = "courier1"
        courier2 = Mock()
        courier2.agent_id = "courier2"
        courier3 = Mock()
        courier3.agent_id = "courier3"
        auction = Mock()

        bid1 = Bid(courier1, auction, 10.0)
        bid2 = Bid(courier2, auction, 5.0)  # Lowest
        bid3 = Bid(courier3, auction, 8.0)

        bids = [bid1, bid2, bid3]
        winner = min(bids, key=lambda b: b.value)

        self.assertEqual(winner, bid2)
        self.assertEqual(winner.value, 5.0)
        self.assertEqual(winner.courier.agent_id, "courier2")

    def test_parcel_journey_state_transitions(self):
        """Test parcel state transitions through its journey"""
        parcel = Parcel("package", 0, 100, 2.0, 10.0)

        # Initial state
        self.assertEqual(parcel.state, "WAITING_PICK_UP")

        # Create pickup stop
        pickup = Stop(parcel.origin, parcel.state, parcel)
        self.assertEqual(pickup.stop_type, "WAITING_PICK_UP")

        # Simulate pickup
        parcel.state = "BEING_DELIVERED"

        # Create delivery stop
        delivery = Stop(parcel.destination, parcel.state, parcel)
        self.assertEqual(delivery.stop_type, "BEING_DELIVERED")

        # Simulate delivery
        parcel.state = "DELIVERED"
        self.assertEqual(parcel.state, "DELIVERED")

    def test_multiple_parcels_multiple_stops(self):
        """Test managing multiple parcels with their stops"""
        parcel1 = Parcel("item1", 0, 50, 1.0, 5.0)
        parcel2 = Parcel("item2", 25, 75, 2.0, 8.0)

        stops = [
            Stop(parcel1.origin, "WAITING_PICK_UP", parcel1),
            Stop(parcel2.origin, "WAITING_PICK_UP", parcel2),
            Stop(parcel1.destination, "BEING_DELIVERED", parcel1),
            Stop(parcel2.destination, "BEING_DELIVERED", parcel2),
        ]

        self.assertEqual(len(stops), 4)
        self.assertEqual(stops[0].parcel, parcel1)
        self.assertEqual(stops[1].parcel, parcel2)

    def test_bid_value_against_parcel_fare(self):
        """Test bid value in relation to parcel fare"""
        parcel = Parcel("item", 0, 100, 1.0, 15.0)
        courier = Mock()
        auction = Mock()
        auction.starting_price = parcel.fare

        # Bid below starting price (should be accepted)
        low_bid = Bid(courier, auction, 10.0)
        self.assertLess(low_bid.value, auction.starting_price)

        # Bid at starting price (should be accepted)
        exact_bid = Bid(courier, auction, 15.0)
        self.assertEqual(exact_bid.value, auction.starting_price)

        # Bid above starting price (should be rejected)
        high_bid = Bid(courier, auction, 20.0)
        self.assertGreater(high_bid.value, auction.starting_price)


if __name__ == '__main__':
    unittest.main()