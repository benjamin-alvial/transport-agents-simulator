from abc import ABC
from typing import Optional, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from parcel_delivery.core.kernel import Kernel


class Entity(ABC):
    """
    Base class for any active entity in the simulation.

    Entities can schedule their own actions but don't necessarily
    communicate with other entities.

    Examples: Buses (follow fixed routes), Couriers (make decisions)
    """

    def __init__(self, entity_id: str):
        self.entity_id = entity_id
        self.sim: Optional["Kernel"] = None

    def schedule_action(self, delay: float, action: Callable, data: dict[str, Any] | None = {}):
        """
        Schedule a future action for this agent.

        Args:
            delay: Time delay before action
            action: Method to call
            data: Optional data for the action
        """
        if self.sim is None:
            raise RuntimeError(f"Entity {self.entity_id} not registered with core")
        return self.sim.schedule(delay, action, data)

    def print_log_message(self, msg: str):
        """"
        Prints the given message preceded by the simulation time at which the event occurs
        """
        t_s = self.sim.current_time
        if t_s < 60:
            formatted_time = f"{t_s:.1f}s"
        elif t_s < 3600:
            m = int(t_s // 60)
            s = t_s % 60
            formatted_time = f"{m}m{s:04.1f}s"
        else:
            h = int(t_s // 3600)
            m = int((t_s % 3600) // 60)
            s = t_s % 60
            formatted_time = f"{h}h{m:02d}m{s:04.1f}s"

        sim_time_string = f"[t={formatted_time}] {self.entity_id}: "
        print(sim_time_string + msg)