"""
Loggers for statistics and debugging.

Contains loggers for different types of events:
    - BaseLogger: base class for all loggers
    - EdgeLogger: logs entry and exits of edges
"""
from .base_logger import BaseLogger
from .edge_logger import EdgeLogger

__all__ = [
    "BaseLogger",
    "EdgeLogger",
]