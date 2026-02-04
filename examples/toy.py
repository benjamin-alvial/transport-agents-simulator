# Example usage and testing
from parcel_delivery import Platform, Customer, Courier, Parcel, Kernel, Bus, Network

if __name__ == "__main__":
    # Example: Toy network
    print("\n=== Example: Toy Network ===")
    network = Network()

    # Create a toy network
    #  0---1---2---3
    #      | /
    #      4

    positions = [
        (0.0, 0.1), (0.1, 0.1), (0.2, 0.1), (0.3, 0.1), (0.1, 0.0)
    ]

    for i, (x, y) in enumerate(positions):
        network.add_node(i, x, y, f"N{i}")

    # Add edges
    network.add_edge(0, 1)
    network.add_edge(1, 2)
    network.add_edge(2, 3)
    # network.add_edge(4, 1)
    network.add_edge(4, 2, 0.35)

    print(f"Network: {network}")
    path_nodes, path_edges, dist = network.shortest_path(4, 2)
    print(f"Shortest path 0->8: {path_nodes} through {path_edges} (distance: {dist:.2f})")

    # Visualize
    print("\nGenerating visualization...")
    network.visualize(
        highlight_nodes=[4, 2],
        highlight_edges=[(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)],
    )
    network.visualize()

    # ================= BASE BUS FLOW =================
    bus_123 = Bus("bus_123", [0,1,2,3])
    network.add_flows(bus_123.nodes_sequence, 1)

    for u, neighbors in network.edges.items():
        for v, edge in neighbors.items():
            print(f"{edge}: flow = {edge.flow}")

    # # ================= DELIVERY =================
    sim = Kernel()
    sim.set_network(network)

    # Create entities
    platform = Platform("platform")
    customer_sending = Customer("customer_sending", 4)
    courier1 = Courier("courier1", 4, 20, 30)
    courier2 = Courier("courier2", 4, 20, 30)

    sim.register_entity(platform)
    sim.register_entity(customer_sending)
    sim.register_entity(courier1)
    sim.register_entity(courier2)

    sim.schedule(delay=5.0,
                 action=customer_sending.send_delivery_request,
                 data={"parcel": Parcel("laptop", customer_sending.location_node_id, 2, 5, 10),
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

    network.visualize(show_congestion=True)

    network.calculate_delay(bus_123.nodes_sequence)
