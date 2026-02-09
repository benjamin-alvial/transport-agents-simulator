from dataclasses import dataclass

@dataclass
class Occupancy:
    """Represents a vehicle occupying an edge during a time interval"""
    vehicle_id: str
    vehicle_type: str  # "bus", "courier", "car"
    enter_time: float