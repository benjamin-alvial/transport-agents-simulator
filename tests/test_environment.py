import pytest
from unittest.mock import patch
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.environment.network import Network


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_network():
    """Small four-node diamond network for reuse across tests."""
    net = Network()
    net.add_node(Node(1, x=0.0, y=0.0))
    net.add_node(Node(2, x=1.0, y=1.0))
    net.add_node(Node(3, x=2.0, y=0.0))
    net.add_node(Node(4, x=1.0, y=-1.0))
    net.add_edge(Edge(10, from_node=1, to_node=2, distance=100.0, free_flow_speed=14.0))
    net.add_edge(Edge(11, from_node=2, to_node=3, distance=100.0, free_flow_speed=14.0))
    net.add_edge(Edge(12, from_node=1, to_node=4, distance=120.0, free_flow_speed=10.0))
    net.add_edge(Edge(13, from_node=4, to_node=3, distance=120.0, free_flow_speed=10.0))
    return net


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class TestNode:
    def test_attributes(self):
        n = Node(7, x=3.5, y=-2.0)
        assert n.node_id == 7
        assert n.x == 3.5
        assert n.y == -2.0


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

class TestEdge:
    def test_attributes(self):
        e = Edge(5, from_node=1, to_node=2, distance=250.0, free_flow_speed=13.9)
        assert e.edge_id == 5
        assert e.from_node == 1
        assert e.to_node == 2
        assert e.distance == 250.0
        assert e.free_flow_speed == 13.9


# ---------------------------------------------------------------------------
# Network — structure
# ---------------------------------------------------------------------------

class TestNetworkStructure:
    def test_empty_on_init(self):
        net = Network()
        assert net.nodes == {}
        assert net.edges == {}

    def test_add_node_stored_by_id(self):
        net = Network()
        n = Node(1, x=0.0, y=0.0)
        net.add_node(n)
        assert net.nodes[1] is n

    def test_add_multiple_nodes(self):
        net = Network()
        net.add_node(Node(1, 0.0, 0.0))
        net.add_node(Node(2, 1.0, 0.0))
        assert len(net.nodes) == 2

    def test_add_edge_stored_by_id(self):
        net = make_network()
        assert 10 in net.edges
        assert net.edges[10].from_node == 1
        assert net.edges[10].to_node == 2

    def test_add_multiple_edges(self):
        net = make_network()
        assert len(net.edges) == 4

    def test_add_edge_unknown_from_node_raises(self):
        net = Network()
        net.add_node(Node(2, 1.0, 0.0))
        with pytest.raises(KeyError, match="from_node"):
            net.add_edge(Edge(1, from_node=99, to_node=2, distance=50.0, free_flow_speed=10.0))

    def test_add_edge_unknown_to_node_raises(self):
        net = Network()
        net.add_node(Node(1, 0.0, 0.0))
        with pytest.raises(KeyError, match="to_node"):
            net.add_edge(Edge(1, from_node=1, to_node=99, distance=50.0, free_flow_speed=10.0))

    def test_overwrite_node_with_same_id(self):
        net = Network()
        net.add_node(Node(1, 0.0, 0.0))
        net.add_node(Node(1, 5.0, 5.0))
        assert net.nodes[1].x == 5.0

    def test_overwrite_edge_with_same_id(self):
        net = Network()
        net.add_node(Node(1, 0.0, 0.0))
        net.add_node(Node(2, 1.0, 0.0))
        net.add_edge(Edge(10, from_node=1, to_node=2, distance=100.0, free_flow_speed=10.0))
        net.add_edge(Edge(10, from_node=1, to_node=2, distance=200.0, free_flow_speed=20.0))
        assert net.edges[10].distance == 200.0


# ---------------------------------------------------------------------------
# Network — visualize
# ---------------------------------------------------------------------------

class TestNetworkVisualize:
    def test_visualize_runs_without_error(self):
        net = make_network()
        with patch("matplotlib.pyplot.show"):
            net.visualize()

    def test_visualize_empty_network(self):
        net = Network()
        with patch("matplotlib.pyplot.show"):
            net.visualize()
