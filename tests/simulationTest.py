import unittest
from unittest.mock import Mock
import heapq

from parcel_delivery.simulation.kernel import Kernel
from parcel_delivery.simulation.event import Event
from parcel_delivery.simulation.message import Message


class TestEvent(unittest.TestCase):
    """Tests for the Event dataclass"""

    def test_event_creation(self):
        """Test basic event creation"""
        action = Mock()
        event = Event(time=10.0, event_id=1, action=action, data="test_data")

        self.assertEqual(event.time, 10.0)
        self.assertEqual(event.event_id, 1)
        self.assertEqual(event.action, action)
        self.assertEqual(event.data, "test_data")

    def test_event_without_data(self):
        """Test event creation without data"""
        action = Mock()
        event = Event(time=5.0, event_id=0, action=action)

        self.assertEqual(event.time, 5.0)
        self.assertEqual(event.event_id, 0)
        self.assertIsNone(event.data)

    def test_event_execute(self):
        """Test event execution calls action with data"""
        action = Mock(return_value="result")
        event = Event(time=1.0, event_id=0, action=action, data="test")

        result = event.execute()

        action.assert_called_once_with("test")
        self.assertEqual(result, "result")

    def test_event_execute_without_data(self):
        """Test event execution with None data"""
        action = Mock()
        event = Event(time=1.0, event_id=0, action=action)

        event.execute()

        action.assert_called_once_with(None)

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

    def test_schedule_event(self):
        """Test scheduling an event"""
        action = Mock()
        data = "test_data"

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

        event = self.kernel.schedule_at(10.0, action, "data")

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

        def action1(_):
            executed.append(1)

        def action2(_):
            executed.append(2)

        def action3(_):
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

        def stop_action(_):
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
        event2 = self.kernel.schedule(2.0, action)
        event3 = self.kernel.schedule(3.0, action)

        self.assertEqual(event1.event_id, 0)
        self.assertEqual(event2.event_id, 1)
        self.assertEqual(event3.event_id, 2)
        self.assertEqual(self.kernel.event_counter, 3)

    def test_current_time_advances_during_run(self):
        """Test current time advances as events are processed"""
        times = []

        def capture_time(_):
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


if __name__ == '__main__':
    unittest.main()