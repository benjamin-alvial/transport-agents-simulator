from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """
    Message that can be sent between agents.
    """
    sender_id: str
    receiver_id: str
    msg_type: str
    content: Any
    timestamp: float