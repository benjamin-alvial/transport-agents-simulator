import pytest
from parcel_delivery_two.environment.node import Node
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment import matsim_io


# ---------------------------------------------------------------------------
# Minimal MATSim XML used by matsim_io tests
# ---------------------------------------------------------------------------

MATSIM_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<network name="test">
  <nodes>
    <node id="1" x="0" y="0"/>
    <node id="2" x="0" y="5000"/>
    <node id="3" x="8000" y="5000"/>
  </nodes>
  <links>
    <link id="10" from="1" to="2" length="5000.00" capacity="3600" freespeed="27.78" permlanes="1"/>
    <link id="11" from="2" to="3" length="8000.00" capacity="600"  freespeed="13.89" permlanes="1"/>
  </links>
</network>
"""


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
# matsim_io — load_network_from_matsim
# ---------------------------------------------------------------------------

class TestLoadNetworkFromMatsim:
    @pytest.fixture
    def xml_file(self, tmp_path):
        p = tmp_path / "network.xml"
        p.write_text(MATSIM_XML, encoding="utf-8")
        return str(p)

    def test_returns_network(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert isinstance(net, Network)

    def test_node_count(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert len(net.nodes) == 3

    def test_edge_count(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert len(net.edges) == 2

    def test_node_ids_are_int(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert all(isinstance(k, int) for k in net.nodes)

    def test_node_position(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert net.nodes[2].x == 0.0
        assert net.nodes[2].y == 5000.0

    def test_edge_ids_are_int(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert all(isinstance(k, int) for k in net.edges)

    def test_edge_endpoints(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert net.edges[10].from_node == 1
        assert net.edges[10].to_node == 2

    def test_edge_distance(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert net.edges[10].distance == 5000.0

    def test_edge_free_flow_speed(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert net.edges[11].free_flow_speed == pytest.approx(13.89)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            matsim_io.load_network_from_matsim("nonexistent.xml")

    def test_travel_times_empty_before_load(self, xml_file):
        net = matsim_io.load_network_from_matsim(xml_file)
        assert net.edges[10].travel_times == {}


# ---------------------------------------------------------------------------
# matsim_io — load_historic_travel_times
# ---------------------------------------------------------------------------

EVENTS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<events version="1.0">
  <!-- v1 on edge 10: enters t=100, leaves t=200 → 100 s, bin 0 -->
  <event time="100.0" type="entered link" vehicle="v1" link="10"/>
  <event time="200.0" type="left link"    vehicle="v1" link="10"/>
  <!-- v2 on edge 10: enters t=150, leaves t=400 → 250 s, bin 0 -->
  <event time="150.0" type="entered link" vehicle="v2" link="10"/>
  <event time="400.0" type="left link"    vehicle="v2" link="10"/>
  <!-- v1 on edge 11: enters t=1000, leaves t=1200 → 200 s, bin 900 -->
  <event time="1000.0" type="entered link" vehicle="v1" link="11"/>
  <event time="1200.0" type="left link"    vehicle="v1" link="11"/>
  <!-- event referencing unknown edge 99: should be silently ignored -->
  <event time="500.0" type="entered link" vehicle="v3" link="99"/>
  <event time="600.0" type="left link"    vehicle="v3" link="99"/>
  <!-- vehicle enters traffic / vehicle leaves traffic: must be ignored -->
  <event time="50.0"  type="vehicle enters traffic" vehicle="v4" link="10"/>
  <event time="90.0"  type="vehicle leaves traffic" vehicle="v4" link="10"/>
</events>
"""


class TestLoadHistoricTravelTimes:
    @pytest.fixture
    def loaded_net(self, tmp_path):
        net = Network()
        net.add_node(Node(1, 0.0, 0.0))
        net.add_node(Node(2, 0.0, 5000.0))
        net.add_node(Node(3, 8000.0, 5000.0))
        net.add_edge(Edge(10, from_node=1, to_node=2, distance=5000.0, free_flow_speed=27.78))
        net.add_edge(Edge(11, from_node=2, to_node=3, distance=8000.0, free_flow_speed=13.89))
        events_file = tmp_path / "events.xml"
        events_file.write_text(EVENTS_XML, encoding="utf-8")
        matsim_io.load_historic_travel_times(str(events_file), net)
        return net

    def test_travel_times_populated(self, loaded_net):
        assert loaded_net.edges[10].travel_times != {}

    def test_average_across_vehicles(self, loaded_net):
        # v1=100s, v2=250s → average 175s in bin 0
        assert loaded_net.edges[10].travel_times[0] == pytest.approx(175.0)

    def test_single_vehicle_bin(self, loaded_net):
        # v1=200s in bin 900 (t=1000 → bin 900)
        assert loaded_net.edges[11].travel_times[900] == pytest.approx(200.0)

    def test_bin_key_is_bin_start(self, loaded_net):
        # entry at t=100 → bin 0; entry at t=1000 → bin 900
        assert 0 in loaded_net.edges[10].travel_times
        assert 900 in loaded_net.edges[11].travel_times

    def test_no_cross_bin_contamination(self, loaded_net):
        assert 900 not in loaded_net.edges[10].travel_times
        assert 0 not in loaded_net.edges[11].travel_times

    def test_unknown_edge_silently_ignored(self, loaded_net):
        # edge 99 is not in the network; no crash, no spurious keys
        assert all(e.edge_id in (10, 11) for e in loaded_net.edges.values())

    def test_vehicle_enters_traffic_ignored(self, loaded_net):
        # v4 used only vehicle enters/leaves traffic → no entry recorded → no travel time
        # bin 0 on edge 10 only has v1 and v2 samples (175s average), not v4
        assert loaded_net.edges[10].travel_times[0] == pytest.approx(175.0)

    def test_unloaded_edges_stay_empty(self, loaded_net):
        # edge 11 has no data in bin 0
        assert 0 not in loaded_net.edges[11].travel_times

    def test_file_not_found_raises(self, tmp_path):
        net = Network()
        with pytest.raises(FileNotFoundError):
            matsim_io.load_historic_travel_times("nonexistent.xml", net)
