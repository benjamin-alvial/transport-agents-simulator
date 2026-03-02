import json
import matplotlib.pyplot as plt
from typing import Dict

from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge


class Network:
    """A directed road network composed of nodes and edges.

    Nodes represent intersections or points of interest. Edges represent
    directed road segments with a physical distance and a free-flow speed.

    Attributes:
        nodes: Mapping of internal node ID (int) to Node.
        edges: Mapping of internal edge ID (int) to Edge.
        node_id_to_matsim: Mapping of internal node ID to original MATSim ID (str).
        edge_id_to_matsim: Mapping of internal edge ID to original MATSim ID (str).
        matsim_to_node_id: Mapping of original MATSim node ID (str) to internal ID (int).
        matsim_to_edge_id: Mapping of original MATSim edge ID (str) to internal ID (int).
    """

    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.edges: Dict[int, Edge] = {}
        self.node_id_to_matsim: Dict[int, str] = {}
        self.edge_id_to_matsim: Dict[int, str] = {}
        self.matsim_to_node_id: Dict[str, int] = {}
        self.matsim_to_edge_id: Dict[str, int] = {}

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
        are drawn as straight directed arrows between nodes.
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
        """Render an interactive congestion map with a time-bin slider.

        The slider spans a full 24-hour day in 15-minute steps. For each bin:

        * Edges that have data are coloured by the ratio of historic average
          travel time to free-flow travel time (green ≈ 1 → red ≥ 2).
        * Edges that have no data for the current bin are drawn in light grey.

        Falls back to :meth:`visualize` when no historic travel times have
        been loaded on any edge.
        """
        from matplotlib.widgets import Slider
        import matplotlib.cm as cm
        import matplotlib.colors as mcolors

        has_data = any(edge.travel_times for edge in self.edges.values())
        if not has_data:
            self.visualize()
            return

        _BIN_SIZE = 900  # 15 minutes
        all_bins = list(range(0, 86400, _BIN_SIZE))  # 96 bins, 00:00 → 23:45

        cmap = cm.RdYlGn_r
        norm = mcolors.Normalize(vmin=1.0, vmax=2.0)

        fig, ax = plt.subplots(figsize=(12, 8))
        plt.subplots_adjust(bottom=0.15)

        # Nodes are static — draw once
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

        # Edges drawn once; arrow_patch references kept for colour updates
        arrows = {}
        for edge in self.edges.values():
            src = self.nodes[edge.from_node]
            dst = self.nodes[edge.to_node]
            ann = ax.annotate(
                "",
                xy=(dst.x, dst.y),
                xytext=(src.x, src.y),
                arrowprops=dict(
                    arrowstyle="->",
                    color="lightgray",
                    lw=2.0,
                    shrinkA=12,
                    shrinkB=12,
                    connectionstyle=f"arc3,rad=0.1",
                ),
            )
            arrows[edge.edge_id] = ann

        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_aspect("equal")
        title = ax.set_title("")

        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        fig.colorbar(
            sm, ax=ax,
            label="Travel time / free-flow travel time",
            fraction=0.03, pad=0.04,
        )

        slider_ax = fig.add_axes([0.15, 0.05, 0.7, 0.03])
        slider = Slider(
            slider_ax, "Time bin", 0, len(all_bins) - 1,
            valinit=0, valstep=1,
        )

        def _fmt(seconds: int) -> str:
            h, m = divmod(seconds // 60, 60)
            return f"{h:02d}:{m:02d}"

        def _update(val: float) -> None:
            bin_start = all_bins[int(val)]
            for edge in self.edges.values():
                if bin_start in edge.travel_times:
                    free_flow_tt = edge.distance / edge.free_flow_speed
                    ratio = edge.travel_times[bin_start] / free_flow_tt
                    color = cmap(norm(ratio))
                else:
                    color = "lightgray"
                arrows[edge.edge_id].arrow_patch.set_color(color)
            title.set_text(f"Road Network — Congestion at {_fmt(bin_start)}")
            fig.canvas.draw_idle()

        slider.on_changed(_update)
        _update(0)

        plt.show()

    def export_for_sigma(self):

        nodes = [
            {"id": str(n.node_id), "x": n.x, "y": n.y}
            for n in self.nodes.values()
        ]

        links = []
        for edge in self.edges.values():
            free_flow_tt = edge.distance / edge.free_flow_speed if edge.free_flow_speed > 0 else None

            # precompute ratio per bin (null if no data)
            congestion = {}
            if free_flow_tt:
                for bin_start, tt in edge.travel_times.items():
                    congestion[bin_start] = tt / free_flow_tt

            links.append({
                "id": str(edge.edge_id),
                "source": str(edge.from_node),
                "target": str(edge.to_node),
                "congestion": congestion,  # e.g. {0: 1.2, 900: 1.8, ...}
            })

        with open("network.json", "w") as f:
            json.dump({"nodes": nodes, "links": links}, f)