import matplotlib.pyplot as plt
from typing import Dict

from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge


class Network:
    """A directed road network composed of nodes and edges.

    Nodes represent intersections or points of interest. Edges represent
    directed road segments with a physical distance and a free-flow speed.

    Attributes:
        nodes: Mapping of node_id to Node.
        edges: Mapping of edge_id to Edge.
    """

    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[int, Edge] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the network.

        Args:
            node: The Node to add.
        """
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge to the network.

        Args:
            edge: The Edge to add.

        Raises:
            KeyError: If edge.from_node or edge.to_node is not present in
                the network.
        """
        if edge.from_node not in self.nodes:
            raise KeyError(
                f"Cannot add edge {edge.edge_id}: "
                f"from_node {edge.from_node} not found in network."
            )
        if edge.to_node not in self.nodes:
            raise KeyError(
                f"Cannot add edge {edge.edge_id}: "
                f"to_node {edge.to_node} not found in network."
            )
        self.edges[edge.edge_id] = edge

    def visualize(self) -> None:
        """Render a static plot of the network with labeled nodes.

        Nodes are drawn as filled circles with their IDs as labels. Edges
        are drawn as directed arrows between nodes.
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        for edge in self.edges.values():
            src = self.nodes[edge.from_node]
            dst = self.nodes[edge.to_node]
            ax.annotate(
                "",
                xy=(dst.x, dst.y),
                xytext=(src.x, src.y),
                arrowprops=dict(
                    arrowstyle="->",
                    color="gray",
                    lw=1.5,
                    shrinkA=12,
                    shrinkB=12,
                ),
            )

        for node in self.nodes.values():
            ax.scatter(node.x, node.y, s=400, color="steelblue", zorder=5)
            ax.text(
                node.x,
                node.y,
                str(node.node_id),
                fontsize=9,
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                zorder=6,
            )

        ax.set_title("Road Network")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_aspect("equal")
        plt.tight_layout()
        plt.show()

    def visualize_dynamic_congestion(self) -> None:
        """Render a congestion-weighted network visualization.

        Not yet implemented.
        """
        pass
