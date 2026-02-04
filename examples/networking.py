# Example usage and testing
from parcel_delivery import Platform, Customer, Courier, Parcel, Kernel, Network

if __name__ == "__main__":
    # Example: Grid network with shortcuts
    print("\n=== Example: Grid Network ===")
    network = Network()

    # Create a 3x3 grid
    #  0---1---2
    #  |   |   |
    #  3---4---5
    #  |   |   |
    #  6---7---8

    positions = [
        (0, 10), (10, 10), (20, 10),
        (0, 5), (10, 5), (20, 5),
        (0, 0), (10, 0), (20, 0)
    ]

    for i, (x, y) in enumerate(positions):
        network.add_node(i, x, y, f"N{i}")

    # Add horizontal edges
    # noinspection DuplicatedCode
    for row in [0, 3, 6]:
        for i in range(2):
            network.add_edge(row + i, row + i + 1)

    # Add vertical edges
    for col in range(3):
        network.add_edge(col, col + 3)
        network.add_edge(col + 3, col + 6)

    # Add diagonal shortcut
    network.add_edge(0, 4)

    # Add reverse diagonal to visualize bidirectional
    network.add_edge(4,0)

    print(f"Network: {network}")
    path_nodes, path_edges, dist = network.shortest_path(0, 8)
    print(f"Shortest path 0->8: {path_nodes} through {path_edges} (distance: {dist:.2f})")

    # Visualize
    print("\nGenerating visualization...")
    network.visualize(
        highlight_nodes=[0, 8],
        highlight_edges=[(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)],
        consolidation_points_positions={"C1": 0, "C2": 8}
    )
    network.visualize()

    # ================= DELIVERY =================
    sim = Kernel()
    sim.set_network(network)

    # Create entities
    platform = Platform("platform")
    customer_sending = Customer("customer_sending", 0)
    courier1 = Courier("courier1", 0, 20, 30)
    courier2 = Courier("courier2", 0, 20, 30)

    sim.register_entity(platform)
    sim.register_entity(customer_sending)
    sim.register_entity(courier1)
    sim.register_entity(courier2)

    sim.schedule(delay=5.0,
                 action=customer_sending.send_delivery_request,
                 data={"parcel": Parcel("laptop", customer_sending.location_node_id, 8, 5, 10),
                       "platform": platform})

    sim.schedule(delay=5.0,
                 action=platform.register_courier,
                 data={"courier": courier1})

    sim.schedule(delay=5.0,
                 action=platform.register_courier,
                 data={"courier": courier2})

    print("Starting core...\n")
    sim.run(until=100.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")

    for u, neighbors in sim.network.edges.items():
        for v, edge in neighbors.items():
            print(f"{edge}: flow = {edge.flow}")
