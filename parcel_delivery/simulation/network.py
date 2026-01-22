from typing import Dict, List, Tuple
import heapq

from parcel_delivery.models.node import Node


class Network:
    """
    Road network representation using nodes and adjacency lists.
    Supports shortest path calculation and visualization.
    """

    def __init__(self):
        self.nodes: Dict[int, "Node"] = {}
        self.adjacency: Dict[int, Dict[int, float]] = {}
        # adjacency[i][j] = distance from i to j

    def add_node(self, node_id: int, x_coord: float, y_coord: float, label: str = ""):
        """Add a node to the network"""
        self.nodes[node_id] = Node(node_id, x_coord, y_coord, label)
        if node_id not in self.adjacency:
            self.adjacency[node_id] = {}

    def add_edge(self, from_node: int, to_node: int, distance: float = None,
                 bidirectional: bool = False):
        """
        Add an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            distance: Edge length (if None, calculated from node positions)
            bidirectional: If True, add edge in both directions
        """
        # Ensure nodes exist
        if from_node not in self.nodes or to_node not in self.nodes:
            raise ValueError(f"Both nodes must exist before adding edge")

        # Calculate distance from positions if not provided
        if distance is None:
            n1 = self.nodes[from_node]
            n2 = self.nodes[to_node]
            distance = ((n2.x - n1.x) ** 2 + (n2.y - n1.y) ** 2) ** 0.5

        # Add edge
        if from_node not in self.adjacency:
            self.adjacency[from_node] = {}
        self.adjacency[from_node][to_node] = distance

        if bidirectional:
            if to_node not in self.adjacency:
                self.adjacency[to_node] = {}
            self.adjacency[to_node][from_node] = distance

    def get_neighbors(self, node_id: int) -> Dict[int, float]:
        """Get all neighbors of a node with their distances"""
        return self.adjacency.get(node_id, {})

    def shortest_path_distance(self, start: int, end: int) -> float:
        """
        Calculate the shortest path distance using Dijkstra's algorithm.
        Returns infinity if no path exists.
        """
        if start == end:
            return 0.0

        if start not in self.nodes or end not in self.nodes:
            raise ValueError(f"Nodes {start} and {end} must exist")

        # Priority queue: (distance, node)
        pq = [(0.0, start)]
        distances = {start: 0.0}
        visited = set()

        while pq:
            dist, node = heapq.heappop(pq)

            if node in visited:
                continue
            visited.add(node)

            if node == end:
                return dist

            for neighbor, edge_dist in self.get_neighbors(node).items():
                new_dist = dist + edge_dist
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor))

        return float('inf')  # No path found

    def shortest_path(self, start: int, end: int) -> Tuple[List[int], float]:
        """
        Calculate the shortest path using Dijkstra's algorithm.
        Returns (path, distance) where path is list of node IDs.
        """
        if start == end:
            return [start], 0.0

        if start not in self.nodes or end not in self.nodes:
            raise ValueError(f"Nodes {start} and {end} must exist")

        # Priority queue: (distance, node, path)
        pq = [(0.0, start, [start])]
        distances = {start: 0.0}
        visited = set()

        while pq:
            dist, node, path = heapq.heappop(pq)

            if node in visited:
                continue
            visited.add(node)

            if node == end:
                return path, dist

            for neighbor, edge_dist in self.get_neighbors(node).items():
                new_dist = dist + edge_dist
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor, path + [neighbor]))

        return [], float('inf')  # No path found

    def visualize(self,
                  highlight_nodes=None,
                  highlight_edges=None,
                  consolidation_points_positions=None):
        """
        Visualize the directed road network with distances and curved edges.
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyArrowPatch
        except ImportError:
            print("matplotlib not installed. Install with: pip install matplotlib")
            return

        fig, ax = plt.subplots(figsize=(10, 8))

        def is_bidirectional(u, v):
            return v in self.adjacency and u in self.adjacency.get(v, {})

        # -------- Draw edges --------
        for u, neighbors in self.adjacency.items():
            n1 = self.nodes[u]

            for v, dist in neighbors.items():
                n2 = self.nodes[v]

                highlighted = highlight_edges and (u, v) in highlight_edges
                color = "red" if highlighted else "gray"
                width = 2 if highlighted else 1

                # Curve only if edge exists in both directions
                rad = 0.25 if is_bidirectional(u, v) else 0.0
                if rad != 0:
                    rad *= 1 if u < v else -1

                arrow = FancyArrowPatch(
                    (n1.x, n1.y),
                    (n2.x, n2.y),
                    arrowstyle="->",
                    mutation_scale=12,
                    linewidth=width,
                    color=color,
                    alpha=0.7,
                    connectionstyle=f"arc3,rad={rad}",
                    zorder=1,
                )
                ax.add_patch(arrow)

                # ---- distance label ----
                mx = (n1.x + n2.x) / 2
                my = (n1.y + n2.y) / 2

                # offset label perpendicular to edge
                dx = n2.y - n1.y
                dy = n1.x - n2.x
                norm = (dx ** 2 + dy ** 2) ** 0.5 or 1

                offset = 0.35 * rad
                ax.text(
                    mx + offset * dx / norm,
                    my + offset * dy / norm,
                    f"{dist:.1f}",
                    fontsize=8,
                    ha="center",
                    va="center",
                    zorder=3,
                    bbox=dict(boxstyle="round,pad=0.2",
                              fc="white", ec="none", alpha=0.7),
                )

        # -------- Draw nodes --------
        for node_id, node in self.nodes.items():
            highlighted = highlight_nodes and node_id in highlight_nodes
            color = "red" if highlighted else "lightblue"
            size = 100 if highlighted else 50

            ax.scatter(node.x, node.y,
                       s=size, c=color, zorder=2,
                       edgecolors="black", linewidth=1.5)

            label = node.label if getattr(node, "label", None) else str(node_id)
            ax.text(node.x, node.y + 0.5, label,
                    ha="center", fontsize=9,
                    weight="bold" if highlighted else "normal")

        # -------- Consolidation points positions --------
        if consolidation_points_positions:
            for cid, nid in consolidation_points_positions.items():
                if nid in self.nodes:
                    node = self.nodes[nid]
                    ax.scatter(node.x, node.y,
                               c="green", s=100, zorder=3,
                               marker="s", edgecolors="darkgreen",
                               linewidth=2, label=f"CPoint {cid}")

        ax.set_title("Road Network")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)

        if consolidation_points_positions:
            ax.legend()

        plt.tight_layout()
        plt.show()

    def __repr__(self):
        return f"Network({len(self.nodes)} nodes, {sum(len(n) for n in self.adjacency.values())} edges)"


