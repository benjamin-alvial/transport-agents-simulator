from typing import List


class Bus:
    """
    Represents a bus with a fixed timetable.
    """

    def __init__(self, service_id: str, nodes_sequence: List[int]):
        self.service_id = service_id
        self.nodes_sequence = nodes_sequence