from typing import List

from parcel_delivery.loggers.base_logger import BaseLogger
from parcel_delivery.utils.time_utils import format_time


class AlertLogger(BaseLogger):
    filename = "alert_log.csv"

    def log_entry(self, time: float, entity_id: str, bus_list: List[str], from_node: int, to_node: int):
        formatted_time = format_time(time)
        msg = f"{time}, {formatted_time}, {entity_id}, {bus_list}, {from_node}, {to_node}"
        self.entries.append(msg)
