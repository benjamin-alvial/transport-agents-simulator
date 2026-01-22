import unittest
from unittest.mock import Mock, patch
from io import StringIO

from parcel_delivery.simulation.kernel import Kernel
from parcel_delivery.simulation.message import Message
from parcel_delivery.agents.agent import Agent
from parcel_delivery.agents.customer import Customer
from parcel_delivery.agents.courier import Courier
from parcel_delivery.agents.platform import Platform
from parcel_delivery.agents.auction import Auction
from parcel_delivery.models.parcel import Parcel
from parcel_delivery.models.stop import Stop
from parcel_delivery.models.bid import Bid


class TestAgent(unittest.TestCase):
    """Tests for the base Agent class"""

    def setUp(self):
        """Set up test fixtures"""
        self.kernel = Kernel()

        # Create a concrete Agent subclass for testing
        class TestableAgent(Agent):
            def __init__(self, agent_id: str):
                super().__init__(agent_id)
                self.last_message = None
            def receive_message(self, message):
                self.last_message = message

        self.agent = TestableAgent("test_agent")
        self.kernel.register_agent(self.agent)

    def test_agent_initialization(self):
        """Test agent initializes with correct values"""
        agent = self.agent
        self.assertEqual(agent.agent_id, "test_agent")
        self.assertIsNotNone(agent.sim)

    def test_agent_registered_with_kernel(self):
        """Test agent is properly registered with kernel"""
        self.assertEqual(self.agent.sim, self.kernel)
        self.assertIn("test_agent", self.kernel.agents)

    def test_schedule_action_without_sim_raises_error(self):
        """Test scheduling action without registered sim raises error"""

        class UnregisteredAgent(Agent):
            def receive_message(self, message):
                pass

        agent = UnregisteredAgent("unregistered")

        with self.assertRaises(RuntimeError) as context:
            agent.schedule_action(1.0, lambda x: None)

        self.assertIn("not registered", str(context.exception))

    def test_schedule_action_creates_event(self):
        """Test schedule_action creates event in kernel"""
        action = Mock()

        self.agent.schedule_action(5.0, action, {"key": "value"})

        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertEqual(self.kernel.event_queue[0].time, 5.0)

    def test_send_message_without_sim_raises_error(self):
        """Test sending message without registered sim raises error"""

        class UnregisteredAgent(Agent):
            def receive_message(self, message):
                pass

        agent = UnregisteredAgent("unregistered")

        with self.assertRaises(RuntimeError) as context:
            agent.send_message("receiver", "test", "content")

        self.assertIn("not registered", str(context.exception))

    def test_send_message_creates_message(self):
        """Test send_message creates message in kernel"""
        receiver = self.agent.__class__("receiver")
        self.kernel.register_agent(receiver)

        self.agent.send_message("receiver", "test_type", {"data": 123}, delay=2.0)

        # Should create an event for message delivery
        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertEqual(self.kernel.event_queue[0].time, 2.0)


class TestCustomer(unittest.TestCase):
    """Tests for the Customer agent"""

    def setUp(self):
        """Set up test fixtures"""
        self.kernel = Kernel()
        self.customer = Customer("customer1", location=50)
        self.platform = Platform("platform1")

        self.kernel.register_agent(self.customer)
        self.kernel.register_agent(self.platform)

    def test_customer_initialization(self):
        """Test customer initializes correctly"""
        self.assertEqual(self.customer.agent_id, "customer1")
        self.assertEqual(self.customer.location, 50)

    def test_customer_receive_message_does_nothing(self):
        """Test customer receive_message doesn't crash (even though it does nothing)"""
        msg = Message("sender", "customer1", "test", "content", 0.0)

        # Should not raise an error
        self.customer.receive_message(msg)
        # Should not add new events or change state
        self.assertEqual(len(self.kernel.event_queue), 0)
        self.assertEqual(self.customer.agent_id, "customer1")
        self.assertEqual(self.customer.location, 50)

    def test_send_delivery_request(self):
        """Test customer sends delivery request to platform"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        with patch('sys.stdout', new=StringIO()):
            self.customer.send_delivery_request(parcel, self.platform)

        # Should create a message event
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_send_delivery_request_message_content(self):
        """Test delivery request message has correct structure"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        # Mock the platform's receive_message to capture the message
        received_messages = []
        def capture_message(message):
            received_messages.append(message)
        self.platform.receive_message = capture_message

        with patch('sys.stdout', new=StringIO()):
            self.customer.send_delivery_request(parcel, self.platform)

        # Run the simulation to deliver the message
        self.kernel.run()

        # Verify message was received
        self.assertEqual(len(received_messages), 1)
        msg = received_messages[0]
        self.assertEqual(msg.msg_type, "DELIVERY_REQUEST")
        self.assertEqual(msg.content["parcel"], parcel)


class TestPlatform(unittest.TestCase):
    """Tests for the Platform agent"""

    def setUp(self):
        """Set up test fixtures"""
        self.kernel = Kernel()
        self.platform = Platform("platform1")
        self.kernel.register_agent(self.platform)

    def test_platform_initialization(self):
        """Test platform initializes correctly"""
        self.assertEqual(self.platform.agent_id, "platform1")
        self.assertEqual(self.platform.auction_count, 0)
        self.assertEqual(len(self.platform.auctions), 0)
        self.assertEqual(len(self.platform.subscribed_couriers), 0)

    def test_register_courier(self):
        """Test registering a courier to platform"""
        courier = Courier("courier1", 0, 20, 30.0)

        self.platform.register_courier(courier)

        self.assertIn(courier, self.platform.subscribed_couriers)
        self.assertEqual(len(self.platform.subscribed_couriers), 1)

    def test_register_multiple_couriers(self):
        """Test registering multiple couriers"""
        courier1 = Courier("courier1", 0, 20, 30.0)
        courier2 = Courier("courier2", 10, 15, 25.0)

        self.platform.register_courier(courier1)
        self.assertEqual(len(self.platform.subscribed_couriers), 1)
        self.platform.register_courier(courier2)
        self.assertEqual(len(self.platform.subscribed_couriers), 2)

    def test_handle_delivery_request_creates_auction(self):
        """Test handling delivery request creates an auction"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        msg = Message("customer1", "platform1", "DELIVERY_REQUEST", {"parcel": parcel}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            self.platform.receive_message(msg)

        # Should create an auction
        self.assertEqual(len(self.platform.auctions), 1)
        self.assertEqual(self.platform.auction_count, 1)

    def test_handle_delivery_request_registers_auction_with_kernel(self):
        """Test auction is registered with kernel"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        msg = Message("customer1", "platform1", "DELIVERY_REQUEST", {"parcel": parcel}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            self.platform.receive_message(msg)

        # Auction should be registered in kernel
        auction = self.platform.auctions[0]
        self.assertIn(auction.agent_id, self.kernel.agents)

    def test_send_auction_notification_to_couriers(self):
        """Test platform sends auction notifications to subscribed couriers"""
        courier1 = Courier("courier1", 0, 20, 30.0)
        courier2 = Courier("courier2", 10, 15, 25.0)

        self.kernel.register_agent(courier1)
        self.kernel.register_agent(courier2)

        self.platform.register_courier(courier1)
        self.platform.register_courier(courier2)

        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        auction = Auction("auction0", parcel)
        self.kernel.register_agent(auction)

        with patch('sys.stdout', new=StringIO()):
            self.platform.send_auction_notification(auction)

        # Should create 2 message events (one for each courier)
        self.assertEqual(len(self.kernel.event_queue), 2)

    def test_receive_message_routes_correctly(self):
        """Test receive_message routes to correct handler"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        # Test DELIVERY_REQUEST
        with patch.object(self.platform, 'handle_delivery_request') as mock_handler:
            msg = Message("customer1", "platform1", "DELIVERY_REQUEST", {"parcel": parcel}, 0.0)
            self.platform.receive_message(msg)
            mock_handler.assert_called_once_with(msg)


class TestCourier(unittest.TestCase):
    """Tests for the Courier agent"""

    def setUp(self):
        """Set up test fixtures"""
        self.kernel = Kernel()
        self.courier = Courier("courier1", position=0, capacity=20, speed=30.0)
        self.kernel.register_agent(self.courier)

    def test_courier_initialization(self):
        """Test courier initializes correctly"""
        self.assertEqual(self.courier.agent_id, "courier1")
        self.assertEqual(self.courier.position, 0)
        self.assertEqual(self.courier.capacity, 20)
        self.assertEqual(self.courier.speed, 30.0)
        self.assertEqual(len(self.courier.itinerary), 0)
        self.assertEqual(self.courier.current_load, 0)
        self.assertEqual(len(self.courier.carried_parcels), 0)

    def test_receive_message_routes_correctly(self):
        """Test receive_message routes to correct handler"""
        # Test AUCTION_NOTIFICATION
        with patch.object(self.courier, 'handle_auction_notification') as mock_handler:
            msg = Message("platform1", "courier1", "AUCTION_NOTIFICATION", {}, 0.0)
            self.courier.receive_message(msg)
            mock_handler.assert_called_once_with(msg)

        # Test WINNER_NOTIFICATION
        with patch.object(self.courier, 'handle_winner_notification') as mock_handler:
            msg = Message("auction1", "courier1", "WINNER_NOTIFICATION", {}, 0.0)
            self.courier.receive_message(msg)
            mock_handler.assert_called_once_with(msg)

        # Test LOSER_NOTIFICATION
        with patch.object(self.courier, 'handle_loser_notification') as mock_handler:
            msg = Message("auction1", "courier1", "LOSER_NOTIFICATION", {}, 0.0)
            self.courier.receive_message(msg)
            mock_handler.assert_called_once()

    def test_handle_auction_notification_with_fitting_parcel(self):
        """Test courier handles auction notification for parcel that fits"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        auction = Auction("auction1", parcel)
        self.kernel.register_agent(auction)

        msg = Message("platform1", "courier1", "AUCTION_NOTIFICATION", {"auction": auction}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            with patch('random.randint', return_value=5):
                self.courier.handle_auction_notification(msg)

        # Should schedule a bid request
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_handle_auction_notification_with_too_heavy_parcel(self):
        """Test courier rejects parcel that exceeds capacity"""
        # Parcel weighs 25, but capacity is only 20
        parcel = Parcel("heavy", 50, 100, 25.0, 15.0)
        auction = Auction("auction1", parcel)
        self.kernel.register_agent(auction)

        msg = Message("platform1", "courier1", "AUCTION_NOTIFICATION", {"auction": auction}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            self.courier.handle_auction_notification(msg)

        # Should NOT schedule a bid request
        self.assertEqual(len(self.kernel.event_queue), 0)

    def test_handle_winner_notification(self):
        """Test courier handles winning an auction"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        msg = Message("auction1", "courier1", "WINNER_NOTIFICATION", {"parcel": parcel}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            self.courier.handle_winner_notification(msg)

        # Should add stop to schedule
        self.assertEqual(len(self.courier.itinerary), 1)
        self.assertEqual(self.courier.itinerary[0].location, 50)

        # Should schedule start_delivery
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_handle_loser_notification(self):
        """Test courier handles losing an auction"""
        with patch('sys.stdout', new=StringIO()):
            self.courier.handle_loser_notification()

        # Should not add stop to schedule
        self.assertEqual(len(self.courier.itinerary), 0)

        # Should not schedule start_delivery
        self.assertEqual(len(self.kernel.event_queue), 0)

    def test_send_bid_request(self):
        """Test courier sends bid request to auction"""
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        auction = Auction("auction1", parcel)
        self.kernel.register_agent(auction)

        bid = Bid(self.courier, auction, 5)

        with patch('sys.stdout', new=StringIO()):
            self.courier.send_bid_request(bid, auction)

        # Should create message event
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_start_delivery_with_empty_schedule(self):
        """Test start_delivery with empty schedule"""
        with patch('sys.stdout', new=StringIO()) as output:
            self.courier.start_delivery()
            self.assertIn("All deliveries complete", output.getvalue())

    def test_start_delivery_schedules_travel(self):
        """Test start_delivery schedules travel to next stop"""
        parcel = Parcel("laptop", 100, 200, 5.0, 15.0)
        stop = Stop(100, "WAITING_PICK_UP", parcel)
        self.courier.itinerary.append(stop)

        with patch('sys.stdout', new=StringIO()):
            self.courier.start_delivery()

        # Should schedule arrival at stop
        self.assertEqual(len(self.kernel.event_queue), 1)
        # Travel time should be distance/speed = 100/30 ≈ 3.33
        self.assertAlmostEqual(self.kernel.event_queue[0].time, 100 / 30, places=2)

    def test_arrive_at_stop_pickup(self):
        """Test courier arrives at pickup stop"""
        parcel = Parcel("laptop", 100, 200, 5.0, 15.0)
        stop = Stop(100, "WAITING_PICK_UP", parcel)
        self.courier.itinerary.append(stop)

        with patch('sys.stdout', new=StringIO()):
            self.courier.arrive_at_stop(stop)

        # Courier position should update
        self.assertEqual(self.courier.position, 100)

        # Parcel should be in carried parcels
        self.assertIn(parcel, self.courier.carried_parcels)

        # Parcel state should update
        self.assertEqual(parcel.state, "BEING_DELIVERED")

        # Delivery stop should be added
        self.assertEqual(len(self.courier.itinerary), 1)
        self.assertEqual(self.courier.itinerary[0].location, 200)

    def test_arrive_at_stop_delivery(self):
        """Test courier arrives at delivery stop"""
        parcel = Parcel("laptop", 100, 200, 5.0, 15.0)
        parcel.state = "BEING_DELIVERED"
        self.courier.carried_parcels.append(parcel)

        stop = Stop(200, "BEING_DELIVERED", parcel)
        self.courier.itinerary.append(stop)
        self.courier.position = 200

        with patch('sys.stdout', new=StringIO()):
            self.courier.arrive_at_stop(stop)

        # Parcel should be removed from carried parcels
        self.assertNotIn(parcel, self.courier.carried_parcels)

        # Parcel state should update
        self.assertEqual(parcel.state, "DELIVERED")


class TestAuction(unittest.TestCase):
    """Tests for the Auction agent"""

    def setUp(self):
        """Set up test fixtures"""
        self.kernel = Kernel()
        self.parcel = Parcel("laptop", 50, 100, 5.0, 15.0)
        self.auction = Auction("auction1", self.parcel)
        self.kernel.register_agent(self.auction)

    def test_auction_initialization(self):
        """Test auction initializes correctly"""
        self.assertEqual(self.auction.agent_id, "auction1")
        self.assertEqual(self.auction.auctioned_parcel, self.parcel)
        self.assertEqual(self.auction.starting_price, 15.0)
        self.assertEqual(self.auction.duration, 20)
        self.assertEqual(len(self.auction.bids), 0)

    def test_start_bidding(self):
        """Test starting bidding process"""
        with patch('sys.stdout', new=StringIO()):
            self.auction.start_bidding()

        # Should schedule end_bidding
        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertEqual(self.kernel.event_queue[0].time, 20)

    def test_receive_message_routes_correctly(self):
        """Test receive_message routes to correct handler"""
        with patch.object(self.auction, 'handle_bid_request') as mock_handler:
            msg = Message("courier1", "auction1", "BID_REQUEST", {}, 0.0)
            self.auction.receive_message(msg)
            mock_handler.assert_called_once_with(msg)

    def test_handle_bid_request_accepts_valid_bid(self):
        """Test auction accepts bid at or below starting price"""
        courier = Courier("courier1", 0, 20, 30.0)
        self.kernel.register_agent(courier)

        bid = Bid(courier, self.auction, 10.0)  # Below starting price
        msg = Message("courier1", "auction1", "BID_REQUEST", {"bid": bid}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            self.auction.handle_bid_request(msg)

        self.assertEqual(len(self.auction.bids), 1)
        self.assertEqual(self.auction.bids[0], bid)

    def test_handle_bid_request_rejects_high_bid(self):
        """Test auction rejects bid above starting price"""
        courier = Courier("courier1", 0, 20, 30.0)
        self.kernel.register_agent(courier)

        bid = Bid(courier, self.auction, 20.0)  # Above starting price of 15.0
        msg = Message("courier1", "auction1", "BID_REQUEST", {"bid": bid}, 0.0)

        with patch('sys.stdout', new=StringIO()):
            self.auction.handle_bid_request(msg)

        # Bid should not be accepted
        self.assertEqual(len(self.auction.bids), 0)

    def test_determine_winner_selects_lowest_bid(self):
        """Test determine_winner selects courier with the lowest bid"""
        courier1 = Courier("courier1", 0, 20, 30.0)
        courier2 = Courier("courier2", 10, 20, 30.0)
        courier3 = Courier("courier3", 20, 20, 30.0)

        self.kernel.register_agent(courier1)
        self.kernel.register_agent(courier2)
        self.kernel.register_agent(courier3)

        bid1 = Bid(courier1, self.auction, 10.0)
        bid2 = Bid(courier2, self.auction, 5.0)  # Lowest
        bid3 = Bid(courier3, self.auction, 8.0)

        self.auction.bids = [bid1, bid2, bid3]

        winner = self.auction.determine_winner()

        self.assertEqual(winner, courier2)

    def test_end_bidding_sends_notifications(self):
        """Test end_bidding sends winner and loser notifications"""
        courier1 = Courier("courier1", 0, 20, 30.0)
        courier2 = Courier("courier2", 10, 20, 30.0)

        self.kernel.register_agent(courier1)
        self.kernel.register_agent(courier2)

        bid1 = Bid(courier1, self.auction, 10.0)
        bid2 = Bid(courier2, self.auction, 5.0)  # Winner

        self.auction.bids = [bid1, bid2]

        with patch('sys.stdout', new=StringIO()):
            self.auction.end_bidding()

        # Should send 2 messages (1 winner, 1 loser)
        self.assertEqual(len(self.kernel.event_queue), 2)

    def test_send_winner_notification(self):
        """Test sending winner notification"""
        courier = Courier("courier1", 0, 20, 30.0)
        self.kernel.register_agent(courier)

        self.auction.send_winner_notification(courier)

        # Should create message event
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_send_loser_notification(self):
        """Test sending loser notification"""
        courier = Courier("courier1", 0, 20, 30.0)
        self.kernel.register_agent(courier)

        self.auction.send_loser_notification(courier)

        # Should create message event
        self.assertEqual(len(self.kernel.event_queue), 1)


class TestAgentIntegration(unittest.TestCase):
    """Integration tests for agent interactions"""

    def setUp(self):
        """Set up test fixtures"""
        self.kernel = Kernel()

    def test_complete_delivery_workflow(self):
        """Test complete workflow from customer request to delivery"""
        # Create agents
        platform = Platform("platform")
        customer = Customer("customer", 50)
        courier = Courier("courier", 0, 20, 30.0)

        self.kernel.register_agent(platform)
        self.kernel.register_agent(customer)
        self.kernel.register_agent(courier)

        platform.register_courier(courier)

        # Customer requests delivery
        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        with patch('sys.stdout', new=StringIO()):
            with patch('random.randint', return_value=5):
                customer.send_delivery_request(parcel, platform)

                # Run simulation
                self.kernel.run(until=50.0)

        # Verify auction was created
        self.assertEqual(len(platform.auctions), 1)

    def test_multiple_couriers_bidding(self):
        """Test multiple couriers bidding on same auction"""
        platform = Platform("platform")
        courier1 = Courier("courier1", 0, 20, 30.0)
        courier2 = Courier("courier2", 10, 20, 30.0)

        self.kernel.register_agent(platform)
        self.kernel.register_agent(courier1)
        self.kernel.register_agent(courier2)

        platform.register_courier(courier1)
        platform.register_courier(courier2)

        parcel = Parcel("laptop", 50, 100, 5.0, 15.0)

        with patch('sys.stdout', new=StringIO()):
            with patch('random.randint', side_effect=[8, 3]):  # courier2 wins
                customer = Customer("customer", 50)
                self.kernel.register_agent(customer)

                customer.send_delivery_request(parcel, platform)

                # Run simulation
                self.kernel.run(until=50.0)

        # Verify auction received bids
        auction = platform.auctions[0]
        self.assertEqual(len(auction.bids), 2)


if __name__ == '__main__':
    unittest.main()