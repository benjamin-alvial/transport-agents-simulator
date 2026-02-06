from parcel_delivery.loggers.base_logger import BaseLogger
from parcel_delivery.utils.time_utils import format_time


class EventLogger(BaseLogger):
    filename = "event_log.csv"

    def log_entry(self, time: float, entity_id: str, event_msg: str):
        formatted_time = format_time(time)
        event_msg = event_msg.replace(",", "...")
        msg = f"{time}, {formatted_time}, {entity_id}, {event_msg}"
        self.entries.append(msg)
