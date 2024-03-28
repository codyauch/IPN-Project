from typing import List
import json
from ns import ns
from dataclasses import dataclass
from physics_simulation import get_stats

NodeContainer = ns.cppyy.gbl.ns3.NodeContainer
NetDeviceContainer = ns.cppyy.gbl.ns3.NetDeviceContainer
Ipv4InterfaceContainer = ns.cppyy.gbl.ns3.Ipv4InterfaceContainer

ns.cppyy.cppdef(
    """
using namespace ns3;

NodeContainer create_node_pair(NodeContainer nodes, int i, int j) {
    return NodeContainer(nodes.Get(i), nodes.Get(j));
}

void set_down(NodeContainer c, int index, int interface) {
    Ptr<Node> n = c.Get(index);
    Ptr<Ipv4> ipv4 = n->GetObject<Ipv4>();
    ipv4->SetDown(interface);
}

void set_up(NodeContainer c, int index, int interface) {
    Ptr<Node> n = c.Get(index);
    Ptr<Ipv4> ipv4 = n->GetObject<Ipv4>();
    ipv4->SetUp(interface);
}

void print_routing_table() {
    Ipv4GlobalRoutingHelper globalRouting;
    Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper> (&std::cout);
    globalRouting.PrintRoutingTableAllAt (Seconds(0.1), routingStream );
}

int get_num_devices(NodeContainer c, int index) {
    Ptr<Node> n = c.Get(index);

    return n->GetNDevices();
}

int get_netdevice_node_index(NodeContainer c, int node_index, int device_index) {
    Ptr<Channel> ch = c.Get(node_index)->GetDevice(device_index)->GetChannel();
    int i1 = ch->GetDevice(0)->GetNode()->GetId();
    int i2 = ch->GetDevice(1)->GetNode()->GetId();

    return node_index == i1 ? i2 : i1;
}

void set_channel_delay(NodeContainer c, int node_index, int device_index, double seconds) {
    Ptr<Channel> ch = c.Get(node_index)->GetDevice(device_index)->GetChannel();

    ch->SetAttribute("Delay", TimeValue(Seconds(seconds)));
}
"""
)

create_node_pair = ns.cppyy.gbl.create_node_pair
set_down = ns.cppyy.gbl.set_down
set_up = ns.cppyy.gbl.set_up
print_routing_table = ns.cppyy.gbl.print_routing_table
get_num_devices = ns.cppyy.gbl.get_num_devices
get_netdevice_node_index = ns.cppyy.gbl.get_netdevice_node_index
set_channel_delay = ns.cppyy.gbl.set_channel_delay

@dataclass
class Topology:
    nodes: "NodeContainer"
    channel_table: "List[List[NetDeviceContainer|None]]"
    ip_table: "List[List[Ipv4InterfaceContainer|None]]"

@dataclass
class ConnectionData:
    connected: bool
    trans_time: float


def create_topology() -> Topology:
    entities = get_stats(0)
    nodes = ns.network.NodeContainer()
    nodes.Create(len(entities))

    internet = ns.internet.InternetStackHelper()
    internet.Install(nodes)

    ipv4 = ns.internet.Ipv4AddressHelper()
    ipv4.SetBase("10.0.0.0", "255.255.255.0")

    channel_table = []
    ip_table = []
    for i, _ in enumerate(entities):
        channel_row = []
        ip_row = []
        for j, _ in enumerate(entities):
            if j == i:
                channel_row.append(None)
                ip_row.append(None)
            else:
                np = create_node_pair(nodes, i, j)

                # TODO set attributes based on real statistics
                p2p = ns.point_to_point.PointToPointHelper()
                p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("5Mbps"))
                ch = p2p.Install(np)
                channel_row.append(ch)

                ip = ipv4.Assign(ch)
                ip_row.append(ip)

        channel_table.append(channel_row)
        ip_table.append(ip_row)

    # initialize routing database and setup routing tables in the nodes
    ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

    return Topology(
        nodes=nodes,
        channel_table=channel_table,
        ip_table=ip_table,
    )

def install_onoff_app(topology: Topology, index: int, ch_i: int, ch_j: int) -> None:
    port = 9 # Discard port (RFC 863)
    address = topology.ip_table[ch_i][ch_j]
    if address is None:
        return

    onoff = ns.applications.OnOffHelper("ns3::UdpSocketFactory", ns.network.InetSocketAddress(address.GetAddress(1), port).ConvertTo())
    onoff.SetConstantRate(ns.network.DataRate("2kbps"))
    onoff.SetAttribute("PacketSize", ns.core.UintegerValue(50))

    apps = onoff.Install(topology.nodes.Get(index))
    apps.Start(ns.core.Seconds(1.0))
    apps.Stop(ns.core.Seconds(10.0))

def install_sink(topology: Topology, index: int) -> None:
    port = 9 # Discard port (RFC 863)
    sink = ns.applications.PacketSinkHelper("ns3::UdpSocketFactory", ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo())
    apps = sink.Install(topology.nodes.Get(index))
    apps.Start(ns.core.Seconds(1.0))
    apps.Stop(ns.core.Seconds(10.0))

def update_topology(topology: Topology, time: int) -> None:
    entities = get_stats(time)
    print(json.dumps(entities, indent=2))
    for entity in entities:
        id = entity["id"]
        if not entity["can_connect"]:
            # take down each interface starting from index 1 (index 0 is loopback)
            for i in range(1, get_num_devices(topology.nodes, id)):
                set_down(topology.nodes, id, i)
        else:
            conns = {}
            for i, conn in enumerate(entity["connections"]):
                conns[conn["id"]] = ConnectionData(
                    connected=conn["connected"],
                    trans_time=conn["trans_time"],
                )
            for i in range(1, get_num_devices(topology.nodes, id)):
                conn_id = get_netdevice_node_index(topology.nodes, id, i)
                if conn_id in conns and conns[conn_id].connected:
                    set_up(topology.nodes, id, i)
                    set_channel_delay(topology.nodes, id, i, conns[conn_id].trans_time)
                else:
                    set_down(topology.nodes, id, i)

        # TODO update error rate

    ns.internet.Ipv4GlobalRoutingHelper.RecomputeRoutingTables()


def simulate():
    # setup routing recomputation
    ns.Config.SetDefault(
        "ns3::Ipv4GlobalRouting::RespondToInterfaceEvents", ns.core.BooleanValue(True)
    )

    # init logging
    ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
    ns.core.LogComponentEnable("PacketSink", ns.core.LOG_LEVEL_INFO)

    topology = create_topology()
    install_onoff_app(topology, 2, 1, 5)
    install_sink(topology, 5)
    update_topology(topology, 10000)

    # TODO schedule recomputation of state
    print_routing_table()

    ns.core.Simulator.Run()
    ns.core.Simulator.Destroy()


if __name__ == "__main__":
    simulate()
