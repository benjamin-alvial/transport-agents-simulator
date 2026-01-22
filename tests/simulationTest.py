import math
import unittest
from unittest.mock import Mock
import heapq

from parcel_delivery.simulation.kernel import Kernel
from parcel_delivery.simulation.event import Event
from parcel_delivery.simulation.message import Message
from parcel_delivery.simulation.network import Network


class TestEvent(unittest.TestCase):
    """Tests for the Event dataclass"""

    def test_event_creation(self):
        """Test basic event creation"""
        action = Mock()
        event = Event(time=10.0, event_id=1, action=action, data={"test_data":"test_data"})

        self.assertEqual(event.time, 10.0)
        self.assertEqual(event.event_id, 1)
        self.assertEqual(event.action, action)
        self.assertEqual(event.data["test_data"], "test_data")

    def test_event_with_negative_time(self):
        """Test event with negative time"""
        action = Mock()

        with self.assertRaises(ValueError) as context:
            event = Event(time=-10.0, event_id=1, action=action, data={"test_data":"test_data"})

        self.assertIn("positive float", str(context.exception))

    def test_event_without_data(self):
        """Test event creation without data"""
        action = Mock()
        event = Event(time=5.0, event_id=0, action=action)

        self.assertEqual(event.time, 5.0)
        self.assertEqual(event.event_id, 0)
        self.assertEqual(event.data, {})

    def test_event_execute(self):
        """Test event execution calls action with data"""
        action = Mock(return_value="result")
        event = Event(time=1.0, event_id=0, action=action, data={"arg1": "test", "arg2": 42})

        result = event.execute()

        action.assert_called_once_with(arg1="test", arg2=42)
        self.assertEqual(result, "result")

    def test_event_execute_without_data(self):
        """Test event execution with no data"""
        action = Mock()
        event = Event(time=1.0, event_id=0, action=action)

        event.execute()

        action.assert_called_once_with()

    def test_event_ordering_by_time(self):
        """Test events are ordered by time"""
        action = Mock()
        event1 = Event(time=5.0, event_id=1, action=action)
        event2 = Event(time=3.0, event_id=2, action=action)
        event3 = Event(time=10.0, event_id=3, action=action)

        self.assertLess(event2, event1)
        self.assertLess(event1, event3)
        self.assertGreater(event3, event2)

    def test_event_ordering_by_id_when_time_equal(self):
        """Test events with same time are ordered by event_id"""
        action = Mock()
        event1 = Event(time=5.0, event_id=1, action=action)
        event2 = Event(time=5.0, event_id=2, action=action)
        event3 = Event(time=5.0, event_id=0, action=action)

        self.assertLess(event3, event1)
        self.assertLess(event1, event2)

    def test_event_in_heap_queue(self):
        """Test events work correctly in a heap queue"""
        action = Mock()
        events = [
            Event(time=10.0, event_id=3, action=action),
            Event(time=5.0, event_id=1, action=action),
            Event(time=5.0, event_id=2, action=action),
            Event(time=1.0, event_id=0, action=action),
        ]

        heap = []
        for event in events:
            heapq.heappush(heap, event)

        # Pop events and verify they come out in correct order
        popped = []
        while heap:
            popped.append(heapq.heappop(heap))

        self.assertEqual(popped[0].time, 1.0)
        self.assertEqual(popped[0].event_id, 0)
        self.assertEqual(popped[1].time, 5.0)
        self.assertEqual(popped[1].event_id, 1)
        self.assertEqual(popped[2].time, 5.0)
        self.assertEqual(popped[2].event_id, 2)
        self.assertEqual(popped[3].time, 10.0)

    def test_event_action_field_not_compared(self):
        """Test that action field doesn't affect comparison"""
        action1 = Mock()
        action2 = Mock()

        event1 = Event(time=5.0, event_id=1, action=action1)
        event2 = Event(time=5.0, event_id=1, action=action2)

        # Even with different actions, events with same time and id are equal
        self.assertEqual(event1, event2)


class TestKernel(unittest.TestCase):
    """Tests for the Kernel class"""

    def setUp(self):
        """Set up a fresh kernel for each test"""
        self.kernel = Kernel()

    # noinspection DuplicatedCode
    def test_kernel_initialization(self):
        """Test kernel initializes with correct default values"""
        self.assertEqual(self.kernel.current_time, 0.0)
        self.assertEqual(len(self.kernel.event_queue), 0)
        self.assertEqual(self.kernel.event_counter, 0)
        self.assertFalse(self.kernel.running)
        self.assertEqual(len(self.kernel.agents), 0)
        self.assertEqual(self.kernel.network, None)

    def test_register_agent(self):
        """Test registering an agent"""
        agent = Mock()
        agent.agent_id = "agent1"

        self.kernel.register_agent(agent)

        self.assertIn("agent1", self.kernel.agents)
        self.assertEqual(self.kernel.agents["agent1"], agent)
        self.assertEqual(agent.sim, self.kernel)

    def test_register_duplicate_agent_raises_error(self):
        """Test registering duplicate agent raises ValueError"""
        agent1 = Mock()
        agent1.agent_id = "agent1"
        agent2 = Mock()
        agent2.agent_id = "agent1"

        self.kernel.register_agent(agent1)

        with self.assertRaises(ValueError) as context:
            self.kernel.register_agent(agent2)

        self.assertIn("already registered", str(context.exception))

    def test_get_agent(self):
        """Test retrieving an agent by ID"""
        agent = Mock()
        agent.agent_id = "agent1"
        self.kernel.register_agent(agent)

        retrieved = self.kernel.get_agent("agent1")

        self.assertEqual(retrieved, agent)

    def test_get_nonexistent_agent(self):
        """Test getting non-existent agent returns None"""
        result = self.kernel.get_agent("nonexistent")
        self.assertIsNone(result)

    def set_network(self):
        """Set the network for this kernel"""
        network = Mock()
        self.kernel.set_network(network)
        self.assertEqual(self.kernel.network, network)

    def test_schedule_event(self):
        """Test scheduling an event"""
        action = Mock()
        data = {"test_data": "test_data"}

        event = self.kernel.schedule(5.0, action, data)

        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertEqual(event.time, 5.0)
        self.assertEqual(event.action, action)
        self.assertEqual(event.data, data)
        self.assertEqual(self.kernel.event_counter, 1)

    def test_schedule_event_in_running_simulation(self):
        """Test scheduling an event in a simulation with non-zero current time"""
        self.kernel.current_time = 10.0
        action = Mock()

        event = self.kernel.schedule(3.0, action)

        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertEqual(event.time, 13.0)

    def test_schedule_negative_delay_raises_error(self):
        """Test scheduling with negative delay raises ValueError"""
        action = Mock()

        with self.assertRaises(ValueError) as context:
            self.kernel.schedule(-1.0, action)

        self.assertIn("non-negative", str(context.exception))

    def test_schedule_multiple_events_ordered(self):
        """Test multiple events are ordered correctly"""
        action = Mock()

        self.kernel.schedule(10.0, action)
        self.kernel.schedule(5.0, action)
        self.kernel.schedule(15.0, action)

        self.assertEqual(len(self.kernel.event_queue), 3)
        # Peek at first event (should be earliest)
        self.assertEqual(self.kernel.event_queue[0].time, 5.0)
        # Peek at last event (should be latest)
        self.assertEqual(self.kernel.event_queue[2].time, 15.0)

    def test_schedule_at_absolute_time(self):
        """Test scheduling at absolute time"""
        action = Mock()

        event = self.kernel.schedule_at(10.0, action, {"data": "data"})

        self.assertEqual(event.time, 10.0)
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_schedule_at_past_time_raises_error(self):
        """Test scheduling in the past raises ValueError"""
        self.kernel.current_time = 10.0
        action = Mock()

        with self.assertRaises(ValueError) as context:
            self.kernel.schedule_at(5.0, action)

        self.assertIn("past", str(context.exception))

    def test_schedule_at_current_time(self):
        """Test scheduling at current time is allowed"""
        self.kernel.current_time = 5.0
        action = Mock()

        event = self.kernel.schedule_at(5.0, action)

        self.assertEqual(event.time, 5.0)

    def test_send_message(self):
        """Test sending a message between agents"""
        sender = Mock()
        sender.agent_id = "sender"
        receiver = Mock()
        receiver.agent_id = "receiver"

        self.kernel.register_agent(sender)
        self.kernel.register_agent(receiver)

        self.kernel.send_message(
            "sender", "receiver", "offer", {"price": 100}, delay=2.0
        )

        # Should schedule a message delivery event
        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertEqual(self.kernel.event_queue[0].time, 2.0)

    def test_send_message_from_nonexistent_sender(self):
        """Test sending message from non-existent sender raises error"""
        receiver = Mock()
        receiver.agent_id = "receiver"
        self.kernel.register_agent(receiver)

        with self.assertRaises(ValueError) as context:
            self.kernel.send_message("nonexistent", "receiver", "msg", "content")

        self.assertIn("not found", str(context.exception))

    def test_send_message_to_nonexistent_receiver(self):
        """Test sending message to non-existent receiver raises error"""
        sender = Mock()
        sender.agent_id = "sender"
        self.kernel.register_agent(sender)

        with self.assertRaises(ValueError) as context:
            self.kernel.send_message("sender", "nonexistent", "msg", "content")

        self.assertIn("not found", str(context.exception))

    def test_send_message_instant_delivery(self):
        """Test sending message with zero delay"""
        sender = Mock()
        sender.agent_id = "sender"
        receiver = Mock()
        receiver.agent_id = "receiver"

        self.kernel.register_agent(sender)
        self.kernel.register_agent(receiver)

        self.kernel.send_message("sender", "receiver", "msg", "content", delay=0.0)

        self.assertEqual(self.kernel.event_queue[0].time, 0.0)

    def test_run_executes_all_events(self):
        """Test run executes all events in order"""
        executed = []

        def action1():
            executed.append(1)

        def action2():
            executed.append(2)

        def action3():
            executed.append(3)

        self.kernel.schedule(5.0, action1)
        self.kernel.schedule(10.0, action2)
        self.kernel.schedule(3.0, action3)

        self.assertFalse(self.kernel.running)
        self.kernel.run()
        self.assertTrue(self.kernel.running)

        # Events should execute in time order
        self.assertEqual(executed, [3, 1, 2])
        self.assertEqual(self.kernel.current_time, 10.0)

    def test_run_with_until_parameter(self):
        """Test run stops at specified time"""
        action = Mock()

        self.kernel.schedule(5.0, action)
        self.kernel.schedule(15.0, action)
        self.kernel.schedule(25.0, action)

        self.kernel.run(until=20.0)

        # Only first two events should execute
        self.assertEqual(action.call_count, 2)
        self.assertEqual(self.kernel.current_time, 20.0)
        # One event should remain in queue
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_run_until_before_first_event(self):
        """Test run with until before any events"""
        action = Mock()

        self.kernel.schedule(10.0, action)

        self.kernel.run(until=5.0)

        action.assert_not_called()
        self.assertEqual(self.kernel.current_time, 5.0)
        self.assertEqual(len(self.kernel.event_queue), 1)

    def test_run_empty_queue(self):
        """Test run with empty queue doesn't crash"""
        self.kernel.run()
        self.assertEqual(self.kernel.current_time, 0.0)

    def test_stop_during_simulation(self):
        """Test stopping simulation from within an event"""

        def stop_action():
            self.kernel.stop()

        action = Mock()

        self.kernel.schedule(5.0, stop_action)
        self.kernel.schedule(10.0, action)

        self.kernel.run()

        # Second event should not execute
        action.assert_not_called()
        self.assertEqual(self.kernel.current_time, 5.0)
        self.assertEqual(len(self.kernel.event_queue), 1)
        self.assertFalse(self.kernel.running)

    def test_peek_next_event_time(self):
        """Test peeking at next event time"""
        action = Mock()

        self.kernel.schedule(5.0, action)
        self.kernel.schedule(10.0, action)

        next_time = self.kernel.peek_next_event_time()

        self.assertEqual(next_time, 5.0)
        # Queue should remain unchanged
        self.assertEqual(len(self.kernel.event_queue), 2)

    def test_peek_empty_queue(self):
        """Test peeking at empty queue returns None"""
        result = self.kernel.peek_next_event_time()
        self.assertIsNone(result)

    # noinspection DuplicatedCode
    def test_reset(self):
        """Test resetting the kernel"""
        # Set up some state
        agent = Mock()
        agent.agent_id = "agent1"
        self.kernel.register_agent(agent)
        self.kernel.schedule(5.0, Mock())
        self.kernel.current_time = 10.0
        self.kernel.running = True

        # Reset
        self.kernel.reset()

        # Verify everything is back to initial state
        self.assertEqual(self.kernel.current_time, 0.0)
        self.assertEqual(len(self.kernel.event_queue), 0)
        self.assertEqual(self.kernel.event_counter, 0)
        self.assertFalse(self.kernel.running)
        self.assertEqual(len(self.kernel.agents), 0)

    def test_event_counter_increments(self):
        """Test event counter increments for each scheduled event"""
        action = Mock()

        event1 = self.kernel.schedule(1.0, action)
        self.assertEqual(self.kernel.event_counter, 1)
        event2 = self.kernel.schedule(2.0, action)
        self.assertEqual(self.kernel.event_counter, 2)
        event3 = self.kernel.schedule(3.0, action)
        self.assertEqual(self.kernel.event_counter, 3)

        self.assertEqual(event1.event_id, 0)
        self.assertEqual(event2.event_id, 1)
        self.assertEqual(event3.event_id, 2)

    def test_current_time_advances_during_run(self):
        """Test current time advances as events are processed"""
        times = []

        def capture_time():
            times.append(self.kernel.current_time)

        self.kernel.schedule(5.0, capture_time)
        self.kernel.schedule(10.0, capture_time)
        self.kernel.schedule(15.0, capture_time)

        self.kernel.run()

        self.assertEqual(times, [5.0, 10.0, 15.0])


class TestMessage(unittest.TestCase):
    """Tests for the Message dataclass"""

    def test_message_creation(self):
        """Test basic message creation"""
        msg = Message(
            sender_id="agent1",
            receiver_id="agent2",
            msg_type="offer",
            content={"price": 100},
            timestamp=5.0
        )

        self.assertEqual(msg.sender_id, "agent1")
        self.assertEqual(msg.receiver_id, "agent2")
        self.assertEqual(msg.msg_type, "offer")
        self.assertEqual(msg.content, {"price": 100})
        self.assertEqual(msg.timestamp, 5.0)

    def test_message_with_different_content_types(self):
        """Test message with various content types"""
        # String content
        msg1 = Message("a1", "a2", "text", "hello", 1.0)
        self.assertEqual(msg1.content, "hello")

        # List content
        msg2 = Message("a1", "a2", "list", [1, 2, 3], 2.0)
        self.assertEqual(msg2.content, [1, 2, 3])

        # None content
        msg3 = Message("a1", "a2", "empty", None, 3.0)
        self.assertIsNone(msg3.content)

        # Complex object content
        msg4 = Message("a1", "a2", "object", {"a": 1, "b": [2, 3]}, 4.0)
        self.assertEqual(msg4.content["a"], 1)

    def test_message_equality(self):
        """Test message equality comparison"""
        msg1 = Message("a1", "a2", "offer", 100, 5.0)
        msg2 = Message("a1", "a2", "offer", 100, 5.0)
        msg3 = Message("a1", "a2", "offer", 200, 5.0)

        self.assertEqual(msg1, msg2)
        self.assertNotEqual(msg1, msg3)

    def test_message_immutability_concept(self):
        """Test that message fields can be accessed"""
        msg = Message("sender", "receiver", "type", "content", 1.0)

        # Dataclasses are mutable by default, but we can verify fields exist
        self.assertTrue(hasattr(msg, 'sender_id'))
        self.assertTrue(hasattr(msg, 'receiver_id'))
        self.assertTrue(hasattr(msg, 'msg_type'))
        self.assertTrue(hasattr(msg, 'content'))
        self.assertTrue(hasattr(msg, 'timestamp'))


class TestNetwork(unittest.TestCase):
    """Test basic Network functionality"""

    def setUp(self):
        """Create a fresh network for each test"""
        self.network = Network()

    def test_empty_network(self):
        """Test newly created network is empty"""
        self.assertEqual(len(self.network.nodes), 0)
        self.assertEqual(len(self.network.adjacency), 0)

    def test_add_single_node(self):
        """Test adding a single node"""
        self.network.add_node(0, 5.0, 10.0)
        self.assertEqual(len(self.network.nodes), 1)
        self.assertIn(0, self.network.nodes)
        self.assertEqual(self.network.nodes[0].x, 5.0)
        self.assertEqual(self.network.nodes[0].y, 10.0)

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes"""
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 10.0, 0.0)
        self.network.add_node(2, 20.0, 0.0)
        self.assertEqual(len(self.network.nodes), 3)

    def test_add_node_with_label(self):
        """Test adding node with label"""
        self.network.add_node(0, 0.0, 0.0, label="Depot")
        self.assertEqual(self.network.nodes[0].label, "Depot")

    def test_add_edge_without_nodes_raises_error(self):
        """Test that adding edge without nodes raises error"""
        with self.assertRaises(ValueError):
            self.network.add_edge(0, 1)

    def test_add_edge_calculates_distance(self):
        """Test that edge distance is calculated from node positions"""
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 3.0, 4.0)  # Distance should be 5.0
        self.network.add_edge(0, 1)

        self.assertIn(1, self.network.adjacency[0])
        self.assertAlmostEqual(self.network.adjacency[0][1], 5.0)

    def test_add_edge_with_explicit_distance(self):
        """Test adding edge with explicit distance"""
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 10.0, 0.0)
        self.network.add_edge(0, 1, distance=15.0)

        self.assertAlmostEqual(self.network.adjacency[0][1], 15.0)

    def test_add_edge_bidirectional(self):
        """Test that bidirectional edges are created by default"""
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 10.0, 0.0)
        self.network.add_edge(0, 1, bidirectional=True)

        self.assertIn(1, self.network.adjacency[0])
        self.assertIn(0, self.network.adjacency[1])
        self.assertEqual(self.network.adjacency[0][1],
                         self.network.adjacency[1][0])

    def test_add_edge_unidirectional(self):
        """Test adding unidirectional edge"""
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 10.0, 0.0)
        self.network.add_edge(0, 1, bidirectional=False)

        self.assertIn(1, self.network.adjacency[0])
        self.assertNotIn(0, self.network.adjacency[1])

    def test_get_neighbors_empty(self):
        """Test getting neighbors of node with no edges"""
        self.network.add_node(0, 0.0, 0.0)
        neighbors = self.network.get_neighbors(0)
        self.assertEqual(len(neighbors), 0)

    def test_get_neighbors_nonexistent_node(self):
        """Test getting neighbors of nonexistent node"""
        neighbors = self.network.get_neighbors(999)
        self.assertEqual(len(neighbors), 0)

    def test_get_neighbors(self):
        """Test getting neighbors of a node"""
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 10.0, 0.0)
        self.network.add_node(2, 20.0, 0.0)
        self.network.add_edge(0, 1)
        self.network.add_edge(0, 2)

        neighbors = self.network.get_neighbors(0)
        self.assertEqual(len(neighbors), 2)
        self.assertIn(1, neighbors)
        self.assertIn(2, neighbors)


class TestShortestPath(unittest.TestCase):
    """Test shortest path algorithms"""

    def setUp(self):
        """Create a simple network for testing"""
        self.network = Network()

        # Create a simple line: 0--10--1--10--2
        self.network.add_node(0, 0.0, 0.0)
        self.network.add_node(1, 10.0, 0.0)
        self.network.add_node(2, 20.0, 0.0)
        self.network.add_edge(0, 1)
        self.network.add_edge(1, 2)

    def test_shortest_path_same_node(self):
        """Test shortest path from node to itself"""
        path, dist = self.network.shortest_path(0, 0)
        self.assertEqual(path, [0])
        self.assertEqual(dist, 0.0)

    def test_shortest_path_distance_same_node(self):
        """Test shortest path distance from node to itself"""
        dist = self.network.shortest_path_distance(0, 0)
        self.assertEqual(dist, 0.0)

    def test_shortest_path_direct_edge(self):
        """Test shortest path over single edge"""
        path, dist = self.network.shortest_path(0, 1)
        self.assertEqual(path, [0, 1])
        self.assertAlmostEqual(dist, 10.0)

    def test_shortest_path_multiple_edges(self):
        """Test shortest path over multiple edges"""
        path, dist = self.network.shortest_path(0, 2)
        self.assertEqual(path, [0, 1, 2])
        self.assertAlmostEqual(dist, 20.0)

    def test_shortest_path_nonexistent_start(self):
        """Test shortest path with nonexistent start node"""
        with self.assertRaises(ValueError):
            self.network.shortest_path(999, 0)

    def test_shortest_path_nonexistent_end(self):
        """Test shortest path with nonexistent end node"""
        with self.assertRaises(ValueError):
            self.network.shortest_path(0, 999)

    def test_shortest_path_disconnected(self):
        """Test shortest path between disconnected nodes"""
        self.network.add_node(3, 30.0, 0.0)  # Isolated node

        path, dist = self.network.shortest_path(0, 3)
        self.assertEqual(path, [])
        self.assertEqual(dist, float('inf'))

    def test_shortest_path_distance_disconnected(self):
        """Test shortest path distance between disconnected nodes"""
        self.network.add_node(3, 30.0, 0.0)  # Isolated node

        dist = self.network.shortest_path_distance(0, 3)
        self.assertEqual(dist, float('inf'))

    def test_shortest_path_with_shortcut(self):
        """Test that shortest path finds shortcuts"""
        # Add a direct edge 0->2 with shorter distance
        self.network.add_edge(0, 2, distance=15.0)

        path, dist = self.network.shortest_path(0, 2)
        # Should take direct route, not via node 1
        self.assertEqual(path, [0, 2])
        self.assertAlmostEqual(dist, 15.0)


class TestComplexNetworks(unittest.TestCase):
    """Test with more complex network topologies"""

    def test_grid_network(self):
        """Test shortest path in a grid network"""
        network = Network()

        # Create 3x3 grid:
        # 0---1---2
        # |   |   |
        # 3---4---5
        # |   |   |
        # 6---7---8

        for i in range(9):
            row = i // 3
            col = i % 3
            network.add_node(i, col * 10.0, row * 10.0)

        # Horizontal edges
        for row in [0, 3, 6]:
            for i in range(2):
                network.add_edge(row + i, row + i + 1)

        # Vertical edges
        for col in range(3):
            network.add_edge(col, col + 3)
            network.add_edge(col + 3, col + 6)

        # Test path from corner to corner
        path, dist = network.shortest_path(0, 8)
        self.assertEqual(len(path), 5)  # Should go through 4 intermediate nodes
        self.assertAlmostEqual(dist, 40.0)  # 4 edges of length 10

    def test_grid_with_diagonal(self):
        """Test that diagonal shortcuts are found"""
        network = Network()

        # Create 3x3 grid with diagonal shortcut
        for i in range(9):
            row = i // 3
            col = i % 3
            network.add_node(i, col * 10.0, row * 10.0)

        # Add edges as before
        for row in [0, 3, 6]:
            for i in range(2):
                network.add_edge(row + i, row + i + 1)
        for col in range(3):
            network.add_edge(col, col + 3)
            network.add_edge(col + 3, col + 6)

        # Add diagonal shortcut from 0 to 8
        network.add_edge(0, 8, distance=20.0)

        path, dist = network.shortest_path(0, 8)
        self.assertEqual(path, [0, 8])  # Should take diagonal
        self.assertAlmostEqual(dist, 20.0)

    def test_weighted_edges(self):
        """Test that algorithm respects edge weights"""
        network = Network()

        # Create triangle: 0--1--2 with edge back 0--2
        network.add_node(0, 0.0, 0.0)
        network.add_node(1, 10.0, 0.0)
        network.add_node(2, 5.0, 10.0)

        network.add_edge(0, 1, distance=10.0)
        network.add_edge(1, 2, distance=10.0)
        network.add_edge(0, 2, distance=25.0)  # Longer direct route

        # Should go via node 1
        path, dist = network.shortest_path(0, 2)
        self.assertEqual(path, [0, 1, 2])
        self.assertAlmostEqual(dist, 20.0)

    def test_multiple_paths_same_length(self):
        """Test with multiple equally short paths"""
        network = Network()

        # Create diamond:
        #     1
        #    / \
        #   0   3
        #    \ /
        #     2

        network.add_node(0, 0.0, 5.0)
        network.add_node(1, 5.0, 10.0)
        network.add_node(2, 5.0, 0.0)
        network.add_node(3, 10.0, 5.0)

        network.add_edge(0, 1, distance=10.0)
        network.add_edge(0, 2, distance=10.0)
        network.add_edge(1, 3, distance=10.0)
        network.add_edge(2, 3, distance=10.0)

        path, dist = network.shortest_path(0, 3)
        # Should find one of the two equally short paths
        self.assertAlmostEqual(dist, 20.0)
        self.assertIn(len(path), [3])  # 3 nodes in path
        self.assertEqual(path[0], 0)
        self.assertEqual(path[-1], 3)


class TestNetworkRepr(unittest.TestCase):
    """Test network string representation"""

    def test_empty_network_repr(self):
        """Test repr of empty network"""
        network = Network()
        repr_str = repr(network)
        self.assertIn("0 nodes", repr_str)
        self.assertIn("0 edges", repr_str)

    def test_network_with_nodes_repr(self):
        """Test repr with nodes and edges"""
        network = Network()
        network.add_node(0, 0.0, 0.0)
        network.add_node(1, 10.0, 0.0)
        network.add_node(2, 15.0, 0.0)
        network.add_edge(0, 1)
        network.add_edge(0, 2)

        repr_str = repr(network)
        self.assertIn("3 nodes", repr_str)
        self.assertIn("2 edges", repr_str)  # Bidirectional = 2 edges


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def test_add_edge_to_same_node(self):
        """Test adding self-loop"""
        network = Network()
        network.add_node(0, 0.0, 0.0)
        network.add_edge(0, 0, distance=5.0)

        self.assertIn(0, network.adjacency[0])
        self.assertEqual(network.adjacency[0][0], 5.0)

    def test_overwrite_edge(self):
        """Test that adding edge twice overwrites"""
        network = Network()
        network.add_node(0, 0.0, 0.0)
        network.add_node(1, 10.0, 0.0)

        network.add_edge(0, 1, distance=10.0)
        network.add_edge(0, 1, distance=20.0)  # Overwrite

        self.assertEqual(network.adjacency[0][1], 20.0)

    def test_large_network_performance(self):
        """Test that algorithm works with larger networks"""
        network = Network()

        # Create a line of 100 nodes
        for i in range(100):
            network.add_node(i, i * 10.0, 0.0)

        for i in range(99):
            network.add_edge(i, i + 1)

        # Should handle this efficiently
        path, dist = network.shortest_path(0, 99)
        self.assertEqual(len(path), 100)
        self.assertAlmostEqual(dist, 990.0)

    def test_negative_coordinates(self):
        """Test nodes with negative coordinates"""
        network = Network()
        network.add_node(0, -10.0, -5.0)
        network.add_node(1, 10.0, 5.0)
        network.add_edge(0, 1)

        # Distance should be sqrt(400 + 100) = sqrt(500) ≈ 22.36
        expected_dist = math.sqrt(400 + 100)
        self.assertAlmostEqual(network.adjacency[0][1], expected_dist, places=2)


if __name__ == '__main__':
    unittest.main()