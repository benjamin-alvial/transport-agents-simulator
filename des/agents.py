from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, TYPE_CHECKING

from .message import Message  # Relative import

if TYPE_CHECKING:
    from .kernel import SimulationKernel


class Agent(ABC):
    """
    Base class for all agents in the simulation.
    
    Agents can:
    - Receive messages from other agents
    - Schedule their own future actions
    - Maintain internal state
    """
    def __init__(self, agent_id: str):
        self.agent_id: str = agent_id
        self.sim: Optional[SimulationKernel] = None
    
    @abstractmethod
    def receive_message(self, message: Message):
        """
        Handle incoming messages. Must be implemented by subclasses.
        
        Args:
            message: The incoming message
        """
        pass
    
    def schedule_action(self, delay: float, action: Callable, data: Any = None):
        """
        Schedule a future action for this agent.
        
        Args:
            delay: Time delay before action
            action: Method to call
            data: Optional data for the action
        """
        if self.sim is None:
            raise RuntimeError(f"Agent {self.agent_id} not registered with simulation")
        return self.sim.schedule(delay, action, data)
    
    def send_message(self, receiver_id: str, msg_type: str, 
                     content: Any, delay: float = 0.0):
        """
        Send a message to another agent.
        
        Args:
            receiver_id: ID of receiving agent
            msg_type: Type of message
            content: Message payload
            delay: Delivery delay
        """
        if self.sim is None:
            raise RuntimeError(f"Agent {self.agent_id} not registered with simulation")
        self.sim.send_message(self.agent_id, receiver_id, msg_type, content, delay)
