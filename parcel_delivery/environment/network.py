from typing import Dict, List, Tuple, Optional
import heapq

from parcel_delivery.environment.edge import Edge
from parcel_delivery.environment.node import Node


class Network:
    """
    Road network representation using nodes and edge objects.
    Supports shortest path calculation, congestion modeling, and visualization.
    """

    def __init__(self):
        self.nodes: Dict[int, "Node"] = {}
        self.edges: Dict[int, Dict[int, "Edge"]] = {}
        # edges[from_node][to_node] = Edge object

    def add_node(self, node_id: int, x_coord: float, y_coord: float, label: str = ""):
        """Add a node to the network"""
        self.nodes[node_id] = Node(node_id, x_coord, y_coord, label)
        if node_id not in self.edges:
            self.edges[node_id] = {}

    def add_edge(self, from_node: int, to_node: int, distance: float = None,
                 capacity: float = 10.0, bidirectional: bool = False):
        """
        Add an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            distance: Edge length (if None, calculated from node positions)
            capacity: Maximum vehicles per hour (default 10)
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
        if from_node not in self.edges:
            self.edges[from_node] = {}

        self.edges[from_node][to_node] = Edge(
            from_node=from_node,
            to_node=to_node,
            distance=distance,
            capacity=capacity
        )

        if bidirectional:
            if to_node not in self.edges:
                self.edges[to_node] = {}
            self.edges[to_node][from_node] = Edge(
                from_node=to_node,
                to_node=from_node,
                distance=distance,
                capacity=capacity
            )

    def get_edge(self, from_node: int, to_node: int) -> Optional[Edge]:
        """Get edge between two nodes, or None if it doesn't exist"""
        return self.edges.get(from_node, {}).get(to_node)

    def get_neighbors(self, node_id: int) -> List[int]:
        """Get list of neighbor node IDs"""
        return list(self.edges.get(node_id, {}).keys())

    def add_flows(self, path: List[int], amount: float):
        """Add traffic flows to a list of edges"""
        for i in range(0,len(path)-1):
            edge = self.get_edge(path[i], path[i+1])
            if edge:
                edge.flow += amount

    def add_flow(self, from_node: int, to_node: int, amount: float):
        """Add traffic flow to an edge"""
        edge = self.get_edge(from_node, to_node)
        if edge:
            edge.flow += amount

    def remove_flow(self, from_node: int, to_node: int, amount: float):
        """Remove traffic flow from an edge"""
        edge = self.get_edge(from_node, to_node)
        if edge:
            edge.flow = max(0.0, edge.flow - amount)

    def reset_flows(self):
        """Reset all edge flows to zero"""
        for node_edges in self.edges.values():
            for edge in node_edges.values():
                edge.flow = 0.0

    def get_congested_edges(self, threshold: float = 0.8) -> List[Edge]:
        """Get all edges above congestion threshold"""
        congested = []
        for node_edges in self.edges.values():
            for edge in node_edges.values():
                if edge.is_congested(threshold):
                    congested.append(edge)
        return congested

    def shortest_path_distance(self, start: int, end: int,
                               use_congestion: bool = False) -> float:
        """
        Calculate the shortest path distance using Dijkstra's algorithm.

        Args:
            start: Start node ID
            end: End node ID
            use_congestion: If True, use congestion-adjusted travel times

        Returns:
            Shortest distance (or travel time if use_congestion=True)
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

            for neighbor in self.get_neighbors(node):
                edge = self.edges[node][neighbor]

                # Choose metric based on congestion flag
                if use_congestion:
                    edge_cost = edge.get_travel_time()
                else:
                    edge_cost = edge.distance

                new_dist = dist + edge_cost
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor))

        return float('inf')  # No path found

    def shortest_path(self, start: int, end: int,
                      use_congestion: bool = False) -> Tuple[List[int], List, float]:
        """
        Calculate the shortest path using Dijkstra's algorithm.

        Returns:
            (path_nodes, path_edges, distance)
        """
        if start == end:
            return [start], [], 0.0

        if start not in self.nodes or end not in self.nodes:
            raise ValueError(f"Nodes {start} and {end} must exist")

        # Priority queue: (distance, node, path_nodes, path_edges)
        pq = [(0.0, start, [start], [])]
        distances = {start: 0.0}
        visited = set()

        while pq:
            dist, node, path_nodes, path_edges = heapq.heappop(pq)

            if node in visited:
                continue
            visited.add(node)

            if node == end:
                return path_nodes, path_edges, dist

            for neighbor in self.get_neighbors(node):
                edge = self.edges[node][neighbor]

                edge_cost = (
                    edge.get_travel_time()
                    if use_congestion
                    else edge.distance
                )

                new_dist = dist + edge_cost
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    heapq.heappush(
                        pq,
                        (
                            new_dist,
                            neighbor,
                            path_nodes + [neighbor],
                            path_edges + [edge],
                        ),
                    )

        return [], [], float('inf')  # No path found

    def visualize(self,
                  highlight_nodes=None,
                  highlight_edges=None,
                  consolidation_points_positions=None,
                  show_congestion=False):
        """
        Visualize the directed road network with distances and curved edges.

        Args:
            highlight_nodes: List of node IDs to highlight
            highlight_edges: List of (from, to) tuples to highlight
            consolidation_points_positions: Dict of {point_id: node_id}
            show_congestion: If True, color edges by congestion level
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyArrowPatch
            import matplotlib.colors as mcolors
        except ImportError:
            print("matplotlib not installed. Install with: pip install matplotlib")
            return

        fig, ax = plt.subplots(figsize=(10, 8))

        def is_bidirectional(u, v):
            return v in self.edges and u in self.edges.get(v, {})

        # -------- Draw edges --------
        for u, neighbors in self.edges.items():
            n1 = self.nodes[u]

            for v, edge in neighbors.items():
                n2 = self.nodes[v]

                highlighted = highlight_edges and (u, v) in highlight_edges

                if show_congestion and not highlighted:
                    # Color by congestion ratio
                    ratio = edge.congestion_ratio()
                    if ratio < 0.5:
                        color = "green"
                    elif ratio < 0.8:
                        color = "orange"
                    else:
                        color = "red"
                    width = 1.5
                else:
                    color = "red" if highlighted else "gray"
                    width = 2 if highlighted else 1

                # Curve only if edge exists in both directions
                rad = 0.10 if is_bidirectional(u, v) else 0.0

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

                # Show distance or flow/capacity if showing congestion
                if show_congestion:
                    label_text = f"{edge.flow:.0f}/{edge.capacity:.0f}"
                else:
                    label_text = f"{edge.distance:.1f}"

                ax.text(
                    mx + offset * dx / norm,
                    my + offset * dy / norm,
                    label_text,
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

            label = node.label if node.label else str(node_id)
            ax.text(node.x, node.y, label,
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

        title = "Road Network"
        if show_congestion:
            title += " (Congestion: Green<50%, Orange<80%, Red≥80%)"
        ax.set_title(title)
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)

        if consolidation_points_positions:
            ax.legend()

        plt.tight_layout()
        plt.show()

    def __repr__(self):
        total_edges = sum(len(neighbors) for neighbors in self.edges.values())
        return f"Network({len(self.nodes)} nodes, {total_edges} edges)"