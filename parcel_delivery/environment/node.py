from dataclasses import dataclass


@dataclass
class Node:
    """Represents a location in the network"""
    node_id: int
    x: float
    y: float
    label: str = ""

    def __repr__(self):
        return f"Node({self.node_id}, {self.label or f'({self.x}, {self.y})'})"