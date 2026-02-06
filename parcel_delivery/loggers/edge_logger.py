from parcel_delivery.loggers.base_logger import BaseLogger
from parcel_delivery.utils.time_utils import format_time


class EdgeLogger(BaseLogger):
    filename = "edge_log.csv"

    def log_entry(self, time: float, entity_id: str, edge_action: str, from_node: int, to_node: int, flow: float):
        formatted_time = format_time(time)
        msg = f"{time}, {formatted_time}, {entity_id}, {edge_action}, {from_node}, {to_node}, {flow}"
        self.entries.append(msg)
