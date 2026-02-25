from typing import Optional


class ProhibitEdge:
    def __init__(self, edge_id: int, vehicle_type: Optional[str] = None):
        self.edge_id = edge_id
        self.vehicle_type = vehicle_type
