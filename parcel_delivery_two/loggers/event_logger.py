from parcel_delivery_two.loggers.base_logger import BaseLogger
from parcel_delivery_two.utils.time_utils import format_time


class EventLogger(BaseLogger):
    """Singleton logger for simulation lifecycle events.

    Records high-level events such as journey starts, journey completions,
    and other noteworthy moments for each simulated entity.
    """

    filename = "event_log.csv"

    def log_entry(self, time: float, entity_id: str, event_msg: str) -> None:
        """Record one simulation event.

        Args:
            time: Absolute simulation time in seconds.
            entity_id: Identifier of the entity that generated the event.
            event_msg: Human-readable description of the event. Any literal
                commas are replaced with ``"..."`` to avoid breaking the CSV
                row format.
        """
        formatted_time = format_time(time)
        event_msg = event_msg.replace(",", "...")
        msg = f"{time}, {formatted_time}, {entity_id}, {event_msg}"
        self.entries.append(msg)
