from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass(order=True)
class Event:
    """
    Represents a single event in the simulation.

    Events are ordered by time (earlier events come first).
    If times are equal, they're ordered by event_id for deterministic behavior.
    """
    time: float
    event_id: int = field(compare=True)
    action: Callable = field(compare=False)
    data: Any = field(default=None, compare=False)

    def execute(self):
        return self.action(self.data)