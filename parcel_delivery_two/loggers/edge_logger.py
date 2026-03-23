from parcel_delivery_two.loggers.base_logger import BaseLogger
from parcel_delivery_two.utils.time_utils import format_time


class EdgeLogger(BaseLogger):
    """Singleton logger for edge-entry and edge-exit events.

    Records every time a vehicle or bus enters or exits a network edge,
    including the simulation time, entity identity, action direction,
    and the edge's endpoints.
    """

    filename = "edge_log.csv"

    def log_entry(
        self,
        time: float,
        entity_id: str,
        edge_action: str,
        from_node: int,
        to_node: int,
    ) -> None:
        """Record one edge-traversal event.

        Args:
            time: Absolute simulation time in seconds.
            entity_id: Identifier of the vehicle or bus.
            edge_action: ``"entry"`` when entering the edge,
                ``"exit"`` when leaving it.
            from_node: Origin node ID of the edge.
            to_node: Destination node ID of the edge.
        """
        formatted_time = format_time(time)
        msg = f"{time}, {formatted_time}, {entity_id}, {edge_action}, {from_node}, {to_node}"
        self.entries.append(msg)
