import unittest
from unittest.mock import patch
from io import StringIO

from parcel_delivery import SimulationKernel
from main import Platform, Customer, Courier, Parcel, Stop


class TestParcel(unittest.TestCase):
    """Tests for the Parcel class"""

    def test_parcel_initialization(self):
        parcel = Parcel("laptop", 10, 100, 5.0, 15.0)
        self.assertEqual(parcel.contents, "laptop")
        self.assertEqual(parcel.origin, 10)
        self.assertEqual(parcel.destination, 100)
        self.assertEqual(parcel.weight, 5.0)
        self.assertEqual(parcel.fare, 15.0)
        self.assertIsNone(parcel.id)
        self.assertEqual(parcel.state, "waiting_pick_up")

    def test_parcel_repr(self):
        parcel = Parcel("books", 5, 50, 2.0, 10.0)
        parcel.id = "1"
        repr_str = repr(parcel)
        self.assertIn("id=1", repr_str)
        self.assertIn("contents=books", repr_str)
        self.assertIn("state=waiting_pick_up", repr_str)


class TestStop(unittest.TestCase):
    """Tests for the Stop class"""

    def test_stop_initialization(self):
        parcel = Parcel("socks", 100, 200, 0.5, 5.0)
        stop = Stop(100, "waiting_pick_up", parcel)
        self.assertEqual(stop.location, 100)
        self.assertEqual(stop.type, "waiting_pick_up")
        self.assertEqual(stop.parcel, parcel)


class TestPlatform(unittest.TestCase):
    """Tests for the Platform class"""

    def setUp(self):
        self.sim = SimulationKernel()
        self.platform = Platform("test_platform")
        self.sim.register_agent(self.platform)

    def test_platform_initialization(self):
        self.assertEqual(self.platform.agent_id, "test_platform")
        self.assertEqual(self.platform.parcel_count, 0)
        self.assertEqual(len(self.platform.parcels), 0)

    def test_initialize_deliveries(self):
        parcel1 = Parcel("laptop", 10, 100, 5.0, 15.0)
        parcel2 = Parcel("books", 20, 200, 3.0, 10.0)

        with patch('sys.stdout', new=StringIO()):
            self.platform.initialize_deliveries([parcel1, parcel2])

        self.assertEqual(self.platform.parcel_count, 2)
        self.assertEqual(len(self.platform.parcels), 2)
        self.assertEqual(parcel1.id, "0")
        self.assertEqual(parcel2.id, "1")

    def test_receive_parcel_request(self):
        parcel = Parcel("phone", 30, 300, 0.3, 8.0)
        self.platform.receive_parcel_request(parcel)

        self.assertEqual(self.platform.parcel_count, 1)
        self.assertEqual(parcel.id, "0")
        self.assertIn("0", self.platform.parcels)

    def test_query_parcels(self):
        parcel1 = Parcel("laptop", 10, 100, 5.0, 15.0)
        parcel2 = Parcel("books", 20, 200, 3.0, 10.0)

        self.platform.receive_parcel_request(parcel1)
        self.platform.receive_parcel_request(parcel2)

        with patch('sys.stdout', new=StringIO()):
            parcels = self.platform.query_parcels()

        parcels_list = list(parcels)
        self.assertEqual(len(parcels_list), 2)

    def test_assign_parcel(self):
        parcel = Parcel("tablet", 40, 400, 0.8, 12.0)

        with patch('sys.stdout', new=StringIO()):
            result = self.platform.assign_parcel(parcel)

        self.assertTrue(result)


class TestCustomer(unittest.TestCase):
    """Tests for the Customer class"""

    def setUp(self):
        self.sim = SimulationKernel()
        self.customer = Customer("test_customer", 50)
        self.platform = Platform("test_platform")
        self.sim.register_agent(self.customer)
        self.sim.register_agent(self.platform)

    def test_customer_initialization(self):
        self.assertEqual(self.customer.agent_id, "test_customer")
        self.assertEqual(self.customer.location, 50)

    def test_request_delivery(self):
        parcel = Parcel("gift", 50, 150, 1.0, 7.0)

        with patch('sys.stdout', new=StringIO()):
            self.customer.request_delivery(parcel, self.platform)

        self.assertEqual(self.platform.parcel_count, 1)
        self.assertIn("0", self.platform.parcels)


class TestCourier(unittest.TestCase):
    """Tests for the Courier class"""

    def setUp(self):
        self.sim = SimulationKernel()
        self.courier = Courier("test_courier", 0, 20, 30.0)
        self.platform = Platform("test_platform")
        self.sim.register_agent(self.courier)
        self.sim.register_agent(self.platform)

    def test_courier_initialization(self):
        self.assertEqual(self.courier.agent_id, "test_courier")
        self.assertEqual(self.courier.position, 0)
        self.assertEqual(self.courier.capacity, 20)
        self.assertEqual(self.courier.speed, 30.0)
        self.assertEqual(len(self.courier.schedule), 0)
        self.assertEqual(self.courier.current_load, 0)
        self.assertEqual(len(self.courier.carried_parcels), 0)

    def test_ask_for_parcels_empty_platform(self):
        with patch('sys.stdout', new=StringIO()):
            self.courier.ask_for_parcels(self.platform)

        self.assertEqual(len(self.courier.schedule), 0)

    def test_ask_for_parcels_with_available_parcels(self):
        parcel1 = Parcel("laptop", 100, 200, 5.0, 15.0)
        parcel2 = Parcel("book", 150, 250, 2.0, 10.0)

        self.platform.receive_parcel_request(parcel1)
        self.platform.receive_parcel_request(parcel2)

        with patch('sys.stdout', new=StringIO()):
            self.courier.ask_for_parcels(self.platform)

        # Both parcels should be added to schedule
        self.assertEqual(len(self.courier.schedule), 2)

    def test_ask_for_parcels_capacity_limit(self):
        # Create a courier with limited capacity
        small_courier = Courier("small_courier", 0, 5, 30.0)
        self.sim.register_agent(small_courier)

        # Create parcels that exceed capacity
        parcel1 = Parcel("heavy", 100, 200, 4.0, 15.0)
        parcel2 = Parcel("too_heavy", 150, 250, 3.0, 10.0)

        self.platform.receive_parcel_request(parcel1)
        self.platform.receive_parcel_request(parcel2)

        with patch('sys.stdout', new=StringIO()):
            small_courier.ask_for_parcels(self.platform)

        # Only first parcel should fit
        self.assertEqual(len(small_courier.schedule), 1)

    def test_start_delivery_empty_schedule(self):
        with patch('sys.stdout', new=StringIO()) as output:
            self.courier.start_delivery()
            self.assertIn("All deliveries complete", output.getvalue())

    def test_start_delivery_calculates_travel_time(self):
        parcel = Parcel("package", 100, 200, 1.0, 10.0)
        stop = Stop(100, "waiting_pick_up", parcel)
        self.courier.schedule.append(stop)

        with patch('sys.stdout', new=StringIO()):
            self.courier.start_delivery()

        # Travel time should be distance/speed = 100/30 ≈ 3.33
        # Verify that an action was scheduled
        self.assertTrue(len(self.sim._event_queue) > 0)

    def test_arrive_at_stop_pickup(self):
        parcel = Parcel("package", 100, 200, 1.0, 10.0)
        stop = Stop(100, "waiting_pick_up", parcel)
        self.courier.schedule.append(stop)

        with patch('sys.stdout', new=StringIO()):
            self.courier.arrive_at_stop(stop)

        # Courier should be at new position
        self.assertEqual(self.courier.position, 100)

        # Parcel should be in carried parcels
        self.assertIn(parcel, self.courier.carried_parcels)

        # Parcel state should be updated
        self.assertEqual(parcel.state, "being_delivered")

        # Delivery stop should be added to schedule
        self.assertEqual(len(self.courier.schedule), 1)
        self.assertEqual(self.courier.schedule[0].location, 200)

    def test_arrive_at_stop_delivery(self):
        parcel = Parcel("package", 100, 200, 1.0, 10.0)
        parcel.state = "being_delivered"
        self.courier.carried_parcels.append(parcel)

        stop = Stop(200, "being_delivered", parcel)
        self.courier.schedule.append(stop)

        with patch('sys.stdout', new=StringIO()):
            self.courier.arrive_at_stop(stop)

        # Courier should be at delivery location
        self.assertEqual(self.courier.position, 200)

        # Parcel should be removed from carried parcels
        self.assertNotIn(parcel, self.courier.carried_parcels)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full system"""

    def test_complete_delivery_workflow(self):
        sim = SimulationKernel()

        platform = Platform("platform")
        customer = Customer("customer", 50)
        courier = Courier("courier", 0, 20, 30.0)

        sim.register_agent(platform)
        sim.register_agent(customer)
        sim.register_agent(courier)

        # Initialize parcel
        parcel = Parcel("laptop", 100, 200, 5.0, 15.0)

        with patch('sys.stdout', new=StringIO()):
            # Customer requests delivery
            customer.request_delivery(parcel, platform)

            # Courier asks for parcels
            courier.ask_for_parcels(platform)

            # Verify parcel was added to schedule
            self.assertEqual(len(courier.schedule), 1)
            self.assertEqual(courier.schedule[0].location, 100)

    def test_multiple_parcels_workflow(self):
        sim = SimulationKernel()

        platform = Platform("platform")
        courier = Courier("courier", 0, 20, 30.0)

        sim.register_agent(platform)
        sim.register_agent(courier)

        parcels = [
            Parcel("laptop", 100, 200, 5.0, 15.0),
            Parcel("book", 150, 250, 2.0, 10.0),
            Parcel("phone", 120, 220, 0.5, 8.0)
        ]

        with patch('sys.stdout', new=StringIO()):
            platform.initialize_deliveries(parcels)
            courier.ask_for_parcels(platform)

            # All parcels should fit
            self.assertEqual(len(courier.schedule), 3)


if __name__ == '__main__':
    unittest.main()