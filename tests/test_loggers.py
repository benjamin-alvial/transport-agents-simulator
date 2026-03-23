import pytest
import os
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

from parcel_delivery_two.loggers.base_logger import BaseLogger
from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.loggers.event_logger import EventLogger


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset singleton instances before each test."""
    BaseLogger._instance = None
    EdgeLogger._instance = None
    EventLogger._instance = None
    yield
    # Clean up after test
    BaseLogger._instance = None
    EdgeLogger._instance = None
    EventLogger._instance = None


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


# -----------------------------------------------------------------------------
# BaseLogger - Singleton Pattern
# -----------------------------------------------------------------------------

class TestBaseLoggerSingleton:
    def test_returns_same_instance(self):
        logger1 = BaseLogger()
        logger2 = BaseLogger()
        assert logger1 is logger2

    def test_subclasses_have_separate_singletons(self):
        """Each subclass maintains its own singleton instance."""
        base = BaseLogger()
        edge = EdgeLogger()
        event = EventLogger()
        
        # Each should be a different instance
        assert base is not edge
        assert base is not event
        assert edge is not event
        
        # But same subclass returns same instance
        assert EdgeLogger() is edge
        assert EventLogger() is event

    def test_entries_list_initialized(self):
        logger = BaseLogger()
        assert logger.entries == []
        assert isinstance(logger.entries, list)

    def test_default_filename(self):
        logger = BaseLogger()
        assert logger.filename == "base_log.csv"


# -----------------------------------------------------------------------------
# BaseLogger - log() method
# -----------------------------------------------------------------------------

class TestBaseLoggerLog:
    def test_adds_entry_to_list(self):
        logger = BaseLogger()
        logger.log("test message")
        assert len(logger.entries) == 1
        assert logger.entries[0] == "test message"

    def test_adds_multiple_entries(self):
        logger = BaseLogger()
        logger.log("message 1")
        logger.log("message 2")
        logger.log("message 3")
        assert len(logger.entries) == 3
        assert logger.entries == ["message 1", "message 2", "message 3"]

    @patch('builtins.print')
    def test_prints_message(self, mock_print):
        logger = BaseLogger()
        logger.log("test message")
        mock_print.assert_called_once_with("test message")

    def test_preserves_commas_in_message(self):
        """log() doesn't modify the message - it goes directly to entries."""
        logger = BaseLogger()
        logger.log("a, b, c")
        assert logger.entries[0] == "a, b, c"


# -----------------------------------------------------------------------------
# BaseLogger - dump_to_csv()
# -----------------------------------------------------------------------------

class TestBaseLoggerDumpToCsv:
    def test_creates_csv_file(self, temp_output_dir, reset_loggers):
        logger = BaseLogger()
        logger.entries = ["time, entity, action"]
        
        # Patch the output directory
        original_dir = os.getcwd()
        try:
            os.chdir(temp_output_dir)
            os.chdir("..")  # Go up one level since dump_to_csv uses "output/"
            logger.dump_to_csv()
            
            # Check file was created
            assert os.path.exists(os.path.join("output", "base_log.csv"))
        finally:
            os.chdir(original_dir)

    def test_writes_entries_as_rows(self, tmp_path):
        """Test that entries are split on commas and written as CSV rows."""
        logger = BaseLogger()
        logger.entries = [
            "time, entity, action",
            "1.0, test, start"
        ]
        
        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Change to temp directory and create output subdir
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            logger.dump_to_csv()
            
            # Read the CSV
            with open(output_dir / "base_log.csv", "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            assert len(rows) == 2
            assert rows[0] == ["time", "entity", "action"]
            assert rows[1] == ["1.0", "test", "start"]
        finally:
            os.chdir(original_dir)

    def test_strips_whitespace(self, tmp_path):
        """Test that cell values are stripped of whitespace."""
        logger = BaseLogger()
        logger.entries = ["  time  ,  entity  ,  action  " ]
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            logger.dump_to_csv()
            
            with open(output_dir / "base_log.csv", "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            assert rows[0] == ["time", "entity", "action"]
        finally:
            os.chdir(original_dir)

    def test_overwrites_existing_file(self, tmp_path):
        """Test that dump_to_csv overwrites existing files."""
        logger = BaseLogger()
        logger.entries = ["new, data"]
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create existing file with old data
        existing_file = output_dir / "base_log.csv"
        existing_file.write_text("old,data\n")
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            logger.dump_to_csv()
            
            with open(existing_file, "r") as f:
                content = f.read()
            
            assert "new,data" in content
            assert "old,data" not in content
        finally:
            os.chdir(original_dir)

    def test_empty_entries_creates_empty_file(self, tmp_path):
        """Test that empty entries list creates empty CSV."""
        logger = BaseLogger()
        logger.entries = []
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            logger.dump_to_csv()
            
            with open(output_dir / "base_log.csv", "r") as f:
                content = f.read()
            
            assert content == ""
        finally:
            os.chdir(original_dir)


# -----------------------------------------------------------------------------
# EdgeLogger
# -----------------------------------------------------------------------------

class TestEdgeLogger:
    def test_filename(self):
        logger = EdgeLogger()
        assert logger.filename == "edge_log.csv"

    def test_log_entry_adds_to_entries(self):
        logger = EdgeLogger()
        logger.log_entry(
            time=100.0,
            entity_id="courier_1_car_0",
            edge_action="entry",
            from_node=1,
            to_node=2
        )
        
        assert len(logger.entries) == 1
        entry = logger.entries[0]
        assert "100.0" in entry
        assert "courier_1_car_0" in entry
        assert "entry" in entry
        assert "1" in entry
        assert "2" in entry

    def test_log_entry_formats_time(self):
        logger = EdgeLogger()
        logger.log_entry(
            time=3661.5,  # 1h 1m 1.5s
            entity_id="test",
            edge_action="entry",
            from_node=1,
            to_node=2
        )
        
        entry = logger.entries[0]
        assert "1h01m01.5s" in entry

    def test_log_entry_multiple_calls(self):
        logger = EdgeLogger()
        logger.log_entry(10.0, "v1", "entry", 1, 2)
        logger.log_entry(20.0, "v1", "exit", 2, 3)
        logger.log_entry(30.0, "v2", "entry", 1, 3)
        
        assert len(logger.entries) == 3

    def test_log_entry_entry_and_exit(self):
        logger = EdgeLogger()
        logger.log_entry(10.0, "v1", "entry", 1, 2)
        logger.log_entry(20.0, "v1", "exit", 1, 2)
        
        assert "entry" in logger.entries[0]
        assert "exit" in logger.entries[1]

    def test_log_entry_csv_format(self, tmp_path):
        """Test that log_entry creates proper CSV structure."""
        logger = EdgeLogger()
        logger.log_entry(100.0, "v1", "entry", 1, 2)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            logger.dump_to_csv()
            
            with open(output_dir / "edge_log.csv", "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert len(rows[0]) == 6  # time, formatted_time, entity_id, action, from_node, to_node
            assert rows[0][0] == "100.0"
            assert rows[0][2] == "v1"
            assert rows[0][3] == "entry"
            assert rows[0][4] == "1"
            assert rows[0][5] == "2"
        finally:
            os.chdir(original_dir)

    def test_inherits_from_base_logger(self):
        logger = EdgeLogger()
        assert isinstance(logger, BaseLogger)


# -----------------------------------------------------------------------------
# EventLogger
# -----------------------------------------------------------------------------

class TestEventLogger:
    def test_filename(self):
        logger = EventLogger()
        assert logger.filename == "event_log.csv"

    def test_log_entry_adds_to_entries(self):
        logger = EventLogger()
        logger.log_entry(
            time=100.0,
            entity_id="courier_1_car_0",
            event_msg="Journey started"
        )
        
        assert len(logger.entries) == 1
        entry = logger.entries[0]
        assert "100.0" in entry
        assert "courier_1_car_0" in entry
        assert "Journey started" in entry

    def test_log_entry_formats_time(self):
        logger = EventLogger()
        logger.log_entry(
            time=3661.5,
            entity_id="test",
            event_msg="Test event"
        )
        
        entry = logger.entries[0]
        assert "1h01m01.5s" in entry

    def test_log_entry_replaces_commas(self):
        """EventLogger should replace commas in event_msg with '...'"""
        logger = EventLogger()
        logger.log_entry(
            time=100.0,
            entity_id="v1",
            event_msg="Loading, unloading, and resting"
        )
        
        entry = logger.entries[0]
        assert "Loading... unloading... and resting" in entry
        assert "," not in entry.split(",")[-1]  # Last field (message) has no commas

    def test_log_entry_no_commas_unchanged(self):
        """Messages without commas should not be modified."""
        logger = EventLogger()
        logger.log_entry(100.0, "v1", "Simple message")
        
        assert "Simple message" in logger.entries[0]

    def test_log_entry_multiple_calls(self):
        logger = EventLogger()
        logger.log_entry(10.0, "v1", "Start")
        logger.log_entry(20.0, "v1", "Complete")
        logger.log_entry(30.0, "v2", "Start")
        
        assert len(logger.entries) == 3

    def test_log_entry_csv_format(self, tmp_path):
        """Test that log_entry creates proper CSV structure."""
        logger = EventLogger()
        logger.log_entry(100.0, "v1", "Journey started")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            logger.dump_to_csv()
            
            with open(output_dir / "event_log.csv", "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert len(rows[0]) == 4  # time, formatted_time, entity_id, event_msg
            assert rows[0][0] == "100.0"
            assert rows[0][2] == "v1"
            assert rows[0][3] == "Journey started"
        finally:
            os.chdir(original_dir)

    def test_inherits_from_base_logger(self):
        logger = EventLogger()
        assert isinstance(logger, BaseLogger)


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestLoggersIntegration:
    def test_multiple_loggers_independent(self, tmp_path):
        """Test that EdgeLogger and EventLogger maintain separate entries."""
        edge = EdgeLogger()
        event = EventLogger()
        
        edge.log_entry(10.0, "v1", "entry", 1, 2)
        event.log_entry(10.0, "v1", "Journey started")
        edge.log_entry(20.0, "v1", "exit", 1, 2)
        event.log_entry(20.0, "v1", "Journey complete")
        
        assert len(edge.entries) == 2
        assert len(event.entries) == 2
        
        # Entries should be independent
        assert "entry" in edge.entries[0]
        assert "Journey" in event.entries[0]

    def test_dump_to_csv_creates_separate_files(self, tmp_path):
        """Test that each logger writes to its own file."""
        edge = EdgeLogger()
        event = EventLogger()
        
        edge.log_entry(10.0, "v1", "entry", 1, 2)
        event.log_entry(10.0, "v1", "Started")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            edge.dump_to_csv()
            event.dump_to_csv()
            
            assert (output_dir / "edge_log.csv").exists()
            assert (output_dir / "event_log.csv").exists()
        finally:
            os.chdir(original_dir)

    def test_singleton_state_preserved(self):
        """Test that singleton state is preserved across multiple accesses."""
        edge1 = EdgeLogger()
        edge1.log_entry(10.0, "v1", "entry", 1, 2)
        
        edge2 = EdgeLogger()
        edge2.log_entry(20.0, "v2", "exit", 2, 3)
        
        # Both should see all entries
        assert len(edge1.entries) == 2
        assert len(edge2.entries) == 2
        assert edge1.entries is edge2.entries
