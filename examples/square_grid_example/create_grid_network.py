"""Create a 21x21 square grid network and save as MATSim XML."""

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge


def create_square_grid_network(size: int = 21, spacing: float = 100.0) -> Network:
    """Create a square grid network with bidirectional edges.
    
    Args:
        size: Number of nodes along each dimension (default 21 for 21x21 grid).
        spacing: Distance between adjacent nodes in meters.
    
    Returns:
        Network with nodes and bidirectional edges.
    """
    network = Network()
    
    # Create nodes in a grid
    node_id = 0
    for row in range(size):
        for col in range(size):
            x = col * spacing
            y = row * spacing
            network.add_node(Node(node_id=node_id, x=x, y=y))
            node_id += 1
    
    # Create bidirectional edges
    edge_id = 0
    free_flow_speed = 13.89  # ~50 km/h in m/s
    
    for row in range(size):
        for col in range(size):
            current_node = row * size + col
            
            # Horizontal edge (to the right)
            if col < size - 1:
                right_node = row * size + (col + 1)
                # Forward direction
                network.add_edge(Edge(
                    edge_id=edge_id,
                    from_node=current_node,
                    to_node=right_node,
                    distance=spacing,
                    free_flow_speed=free_flow_speed
                ))
                edge_id += 1
                # Reverse direction
                network.add_edge(Edge(
                    edge_id=edge_id,
                    from_node=right_node,
                    to_node=current_node,
                    distance=spacing,
                    free_flow_speed=free_flow_speed
                ))
                edge_id += 1
            
            # Vertical edge (upwards)
            if row < size - 1:
                up_node = (row + 1) * size + col
                # Forward direction
                network.add_edge(Edge(
                    edge_id=edge_id,
                    from_node=current_node,
                    to_node=up_node,
                    distance=spacing,
                    free_flow_speed=free_flow_speed
                ))
                edge_id += 1
                # Reverse direction
                network.add_edge(Edge(
                    edge_id=edge_id,
                    from_node=up_node,
                    to_node=current_node,
                    distance=spacing,
                    free_flow_speed=free_flow_speed
                ))
                edge_id += 1
    
    return network


def save_network_to_matsim(network: Network, filepath: str) -> None:
    """Save a Network to a MATSim XML file.
    
    Args:
        network: The Network to save.
        filepath: Path to the output XML file.
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v1.dtd">',
        '<network>',
        '    <nodes>'
    ]
    
    # Write nodes
    for node_id, node in network.nodes.items():
        lines.append(f'        <node id="{node_id}" x="{node.x:.2f}" y="{node.y:.2f}"/>')
    
    lines.append('    </nodes>')
    lines.append('    <links>')
    
    # Write links (edges)
    for edge_id, edge in network.edges.items():
        lines.append(
            f'        <link id="{edge_id}" from="{edge.from_node}" '
            f'to="{edge.to_node}" length="{edge.distance:.2f}" '
            f'freespeed="{edge.free_flow_speed:.2f}" capacity="1000.0" permlanes="1.0"/>'
        )
    
    lines.append('    </links>')
    lines.append('</network>')
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))


def main():
    """Generate the 21x21 grid network and save to MATSim XML."""
    print("Creating 21x21 square grid network...")
    
    network = create_square_grid_network(size=21, spacing=100.0)
    
    print(f"Created {len(network.nodes)} nodes and {len(network.edges)} edges")
    
    output_file = "square_grid_21x21_network.xml"
    save_network_to_matsim(network, output_file)
    
    print(f"Saved network to: {output_file}")
    
    # Optional: visualize the network
    # network.visualize()


if __name__ == "__main__":
    main()
