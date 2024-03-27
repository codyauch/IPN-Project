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

void node_set_down(NodeContainer c, int index, int interface) {
    Ptr<Node> n = c.Get(index);
    Ptr<Ipv4> ipv4 = n->GetObject<Ipv4>();
    ipv4->SetDown(interface);
}

void node_set_up(NodeContainer c, int index, int interface) {
    Ptr<Node> n = c.Get(index);
    Ptr<Ipv4> ipv4 = n->GetObject<Ipv4>();
    ipv4->SetUp(interface);
}
"""
)

create_node_pair = ns.cppyy.gbl.create_node_pair
set_down = ns.cppyy.gbl.node_set_down
set_up = ns.cppyy.gbl.node_set_up


@dataclass
class Topology:
    nodes: "NodeContainer"
    channel_table: "List[List[NetDeviceContainer|None]]"
    ip_table: "List[List[Ipv4InterfaceContainer|None]]"


def create_topology() -> Topology:
    entities = get_stats(0)
    print(json.dumps(entities, indent=2))
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
            if j <= i:
                channel_row.append(None)
                ip_row.append(None)
            else:
                np = create_node_pair(nodes, i, j)

                # TODO set attributes based on real statistics
                p2p = ns.point_to_point.PointToPointHelper()
                p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("5Mbps"))
                p2p.SetChannelAttribute("Delay", ns.core.StringValue("2ms"))
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

def install_onoff_app(topology: Topology, index: int, ch_i: int, ch_j: int):
    # ensure lower value comes first
    if ch_i > ch_j:
        ch_i, ch_j = ch_j, ch_i
    elif ch_i == ch_j:
        return

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

def install_sink(topology: Topology, index: int):
    port = 9 # Discard port (RFC 863)
    sink = ns.applications.PacketSinkHelper("ns3::UdpSocketFactory", ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo())
    apps = sink.Install(topology.nodes.Get(index))
    apps.Start(ns.core.Seconds(1.0))
    apps.Stop(ns.core.Seconds(10.0))


def simulate():
    # setup routing recomputation
    ns.Config.SetDefault(
        "ns3::Ipv4GlobalRouting::RespondToInterfaceEvents", ns.core.BooleanValue(True)
    )

    # init logging
    ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
    ns.core.LogComponentEnable("PacketSink", ns.core.LOG_LEVEL_INFO)

    topology = create_topology()
    install_onoff_app(topology, 4, 1, 5)
    install_sink(topology, 5)

    # TODO schedule recomputation of state

    ns.core.Simulator.Run()
    ns.core.Simulator.Destroy()


if __name__ == "__main__":
    simulate()
