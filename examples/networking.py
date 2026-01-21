# Example usage and testing
from parcel_delivery.simulation.network import Network

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
    path, dist = network.shortest_path(0, 8)
    print(f"Shortest path 0->8: {path} (distance: {dist:.2f})")

    # Visualize
    print("\nGenerating visualization...")
    network.visualize(
        highlight_nodes=[0, 8],
        highlight_edges=[(path[i], path[i + 1]) for i in range(len(path) - 1)],
        consolidation_points_positions={"C1": 0, "C2": 8}
    )
    network.visualize()
