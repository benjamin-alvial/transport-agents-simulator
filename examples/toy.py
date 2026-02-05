# Example usage and testing
from parcel_delivery import Platform, Customer, Courier, Parcel, Kernel, Bus, Network

if __name__ == "__main__":
    # Example: Toy network
    print("\n=== Example: Toy Network ===")
    network = Network()

    # Create a toy network
    #  0---1---2---3---4
    #      | /
    #      5

    # All distances in meters
    positions = [
        (0, 100), (100, 100), (200, 100), (300, 100), (400, 100), (100, 0)
    ]

    for i, (x, y) in enumerate(positions):
        network.add_node(i, x, y, f"N{i}")

    # Add edges
    network.add_edge(0, 1)
    network.add_edge(1, 2)
    network.add_edge(2, 3)
    network.add_edge(3, 4)
    network.add_edge(5, 1)
    network.add_edge(5, 2, 500)

    print(f"Network: {network}")
    path_nodes, path_edges, dist = network.shortest_path(5, 4)
    print(f"Shortest path 5->4: {path_nodes} through {path_edges} (distance: {dist:.2f}m)")

    # Visualize
    print("\nGenerating visualization...")
    network.visualize(
        highlight_nodes=[5, 4],
        highlight_edges=[(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)],
    )

    # ================= BASE BUS FLOW =================
    bus_01234 = Bus("bus_01234", [0,1,2,3,4])
    network.add_flows(bus_01234.route, 1) ### CHANGE THIS

    # for u, neighbors in network.edges.items():
    #     for v, edge in neighbors.items():
    #         print(f"{edge}: flow considering bus = {edge.flow}")

    # # ================= DELIVERY =================
    sim = Kernel()
    sim.set_network(network)

    # Create entities
    platform = Platform("platform")
    customer_sending = Customer("customer_sending", 1)
    courier1 = Courier("courier1", 5, 20)
    courier2 = Courier("courier2", 5, 20)

    # Register entities to simulation kernel
    sim.register_entity(platform)
    sim.register_entity(customer_sending)
    sim.register_entity(courier1)
    sim.register_entity(courier2)
    sim.register_entity(bus_01234)

    # Register couriers to platform
    platform.register_courier(courier1)
    platform.register_courier(courier2)

    # Schedule a delivery request
    parcel = Parcel("laptop", customer_sending.location_node_id, 4, 5, 10)
    sim.schedule(delay=0.0,
                 action=customer_sending.send_delivery_request,
                 data={"parcel": parcel,
                       "platform": platform})

    # Schedule a bus departure
    sim.schedule(delay=1800.0,
                 action=bus_01234.start_journey)

    # Run simulation for the 24 hours of the day
    print("Starting simulation...\n")
    sim.run(until=86400)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")

    # for u, neighbors in sim.network.edges.items():
    #     for v, edge in neighbors.items():
    #         print(f"{edge}: flow with buses and couriers = {edge.flow}")

    network.visualize(show_congestion=True)
    network.calculate_delay(bus_01234.route)
