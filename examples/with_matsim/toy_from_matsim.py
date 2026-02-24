# Example usage and testing
import parcel_delivery.environment.matsim_io as matsim_io

if __name__ == "__main__":
    # ================= NETWORK =================
    # Example: Toy network from MATSim
    print("\n=== Example: Toy Network from MATSim ===\n===")
    network = matsim_io.load_network_from_matsim("network_scenario_1.xml")
    matsim_io.load_historic_travel_times("5.events.xml", network)

    path_nodes, path_edges, dist = network.shortest_path(2, 3)
    print(f"Shortest path 2->3 without congestion: {path_nodes} through {path_edges} (distance: {dist:.2f}m)")
    network.visualize(
        highlight_nodes=[2, 3],
        highlight_edges=[(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)],
    )

    edge = network.get_edge(2, 6)
    print(f"Previous travel time: {edge.get_travel_time(28800)}")
    slot = int(28800 // 900) % 96
    edge.historic_travel_times[slot] = 9999999
    print(f"Modified travel time: {edge.get_travel_time(28800)}")

    path_nodes, path_edges, dist = network.shortest_path(2, 3, 28800)
    print(f"Shortest path 2->3 with historic (modified) congestion at 8:00 am: {path_nodes} through {path_edges} (travel time: {dist:.2f}s)")
    network.visualize(
        highlight_nodes=[2, 3],
        highlight_edges=[(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)],
    )

