# Example usage and testing
import parcel_delivery.environment.matsim_io as matsim_io

if __name__ == "__main__":
    # ================= NETWORK =================
    # Example: Toy network from MATSim
    print("\n=== Example: Toy Network from MATSim ===\n===")
    network = matsim_io.load_network_from_matsim("network_scenario_1.xml")

    edge = network.get_edge(2, 6)
    edge.flow = 900
    edge = network.get_edge(6, 3)
    edge.flow = 900

    path_nodes, path_edges, dist = network.shortest_path(2, 3, use_congestion=True)
    print(f"Shortest path 2->3: {path_nodes} through {path_edges} (distance: {dist:.2f}m)")

    # Visualize
    print("\nGenerating visualization...")

    network.visualize(
        highlight_nodes=[2, 3],
        highlight_edges=[(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)],
    )


