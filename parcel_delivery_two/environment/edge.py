class Edge:
    """A directed road segment between two nodes in the network.

    Attributes:
        edge_id: Unique integer identifier for the edge.
        from_node: ID of the origin node.
        to_node: ID of the destination node.
        distance: Length of the segment in metres.
        free_flow_speed: Maximum achievable speed on this segment in m/s.
    """

    def __init__(
        self,
        edge_id: int,
        from_node: int,
        to_node: int,
        distance: float,
        free_flow_speed: float,
    ):
        self.edge_id = edge_id
        self.from_node = from_node
        self.to_node = to_node
        self.distance = distance
        self.free_flow_speed = free_flow_speed
