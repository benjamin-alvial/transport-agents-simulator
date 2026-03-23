class Node:
    """A point in the road network representing an intersection or landmark.

    Attributes:
        node_id: Unique integer identifier for the node.
        x: Horizontal position (e.g. metres or longitude).
        y: Vertical position (e.g. metres or latitude).
    """

    def __init__(self, node_id: int, x: float, y: float):
        self.node_id = node_id
        self.x = x
        self.y = y
