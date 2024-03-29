"""network_sim

run a simulation of interplanetary network
"""

import json
import csv
from dataclasses import dataclass
from typing import List
from ns import ns
from physics_simulation import get_stats

NodeContainer = ns.cppyy.gbl.ns3.NodeContainer
NetDeviceContainer = ns.cppyy.gbl.ns3.NetDeviceContainer
Ipv4InterfaceContainer = ns.cppyy.gbl.ns3.Ipv4InterfaceContainer

ns.cppyy.cppdef(
    """
#include "CPyCppyy/API.h"

using namespace ns3;

// create a NodeContainer with two nodes
NodeContainer create_node_pair(NodeContainer nodes, int i, int j) {
    return NodeContainer(nodes.Get(i), nodes.Get(j));
}

// set an interface to be down
void set_down(NodeContainer c, int index, int interface) {
    Ptr<Node> n = c.Get(index);
    Ptr<Ipv4> ipv4 = n->GetObject<Ipv4>();
    ipv4->SetDown(interface);
}

// set an interface to be up
void set_up(NodeContainer c, int index, int interface) {
    Ptr<Node> n = c.Get(index);
    Ptr<Ipv4> ipv4 = n->GetObject<Ipv4>();
    ipv4->SetUp(interface);
}

// print the global routing table
void print_routing_table() {
    Ipv4GlobalRoutingHelper globalRouting;
    Ptr<OutputStreamWrapper> routingStream = Create<OutputStreamWrapper> (&std::cout);
    globalRouting.PrintRoutingTableAllAt (Seconds(0.1), routingStream );
}

// get the number of devices
int get_num_devices(NodeContainer c, int index) {
    Ptr<Node> n = c.Get(index);

    return n->GetNDevices();
}

// get the index of a netdevice
int get_netdevice_node_index(NodeContainer c, int node_index, int device_index) {
    Ptr<Channel> ch = c.Get(node_index)->GetDevice(device_index)->GetChannel();
    int i1 = ch->GetDevice(0)->GetNode()->GetId();
    int i2 = ch->GetDevice(1)->GetNode()->GetId();

    return node_index == i1 ? i2 : i1;
}

// set the channel delay on a channel
void set_channel_delay(NodeContainer c, int node_index, int device_index, double seconds) {
    Ptr<Channel> ch = c.Get(node_index)->GetDevice(device_index)->GetChannel();

    ch->SetAttribute("Delay", TimeValue(Seconds(seconds)));
}

// Schedule seems to require CPP functions
// This gets around that by calling the python function from CPP
void cpp_update_topology() {
    CPyCppyy::Eval("update_topology()");
}
"""
)

# shorten names of cpp functions
create_node_pair = ns.cppyy.gbl.create_node_pair
set_down = ns.cppyy.gbl.set_down
set_up = ns.cppyy.gbl.set_up
print_routing_table = ns.cppyy.gbl.print_routing_table
get_num_devices = ns.cppyy.gbl.get_num_devices
get_netdevice_node_index = ns.cppyy.gbl.get_netdevice_node_index
set_channel_delay = ns.cppyy.gbl.set_channel_delay
cpp_update_topology = ns.cppyy.gbl.cpp_update_topology

# global vars (we need global state to allow calling Python function from CPP)
GLOBAL_TIME = 10000
GLOBAL_TOPOLOGY = None

# constants
TIME_STEP = 60
SIM_LENGTH = 60 * 60 * 24


@dataclass
class Topology:
    """Topology

    object containing data about Topology
    (we don't really need this tbh, but I'm not about to rewrite this)
    """

    nodes: "NodeContainer"
    num_nodes: int
    channel_table: "List[List[NetDeviceContainer|None]]"
    ip_table: "List[List[Ipv4InterfaceContainer|None]]"


@dataclass
class ConnectionData:
    """ConnectionData

    object containing data about a connection
    """

    connected: bool
    trans_time: float


def create_topology() -> Topology:
    """create_topology

    create a network topology from entities
    """

    ascii = ns.network.AsciiTraceHelper()
    stream = ascii.CreateFileStream("network-sim.tr")

    # get the number of nodes in the network
    entities = get_stats(0)
    nodes = ns.network.NodeContainer()
    num_nodes = len(entities)
    nodes.Create(num_nodes)

    # install internet stack on each node
    internet = ns.internet.InternetStackHelper()
    internet.Install(nodes)

    # setup IPv4
    ipv4 = ns.internet.Ipv4AddressHelper()
    ipv4.SetBase("10.0.0.0", "255.255.255.0")

    # setup channel for each pair of nodes
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

                p2p = ns.point_to_point.PointToPointHelper()
                p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("5Mbps"))
                p2p.EnableAsciiAll(stream)
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
        num_nodes=num_nodes,
        channel_table=channel_table,
        ip_table=ip_table,
    )


def install_onoff_app(topology: Topology, index: int, ch_i: int, ch_j: int) -> None:
    """install_onoff_app

    install an onoff application on a node

    topology - the topology to install on
    index    - the node to install on
    ch_i     - index i to send to
    ch_j     - index j to send to
    """
    port = 9  # Discard port (RFC 863)
    address = topology.ip_table[ch_i][ch_j]
    if address is None:
        return

    onoff = ns.applications.OnOffHelper(
        "ns3::UdpSocketFactory",
        ns.network.InetSocketAddress(address.GetAddress(1), port).ConvertTo(),
    )

    # one packet per TIME_STEP
    rate = 8 / TIME_STEP
    onoff.SetConstantRate(ns.network.DataRate(f"{rate}kbps"))
    onoff.SetAttribute("PacketSize", ns.core.UintegerValue(1024))

    apps = onoff.Install(topology.nodes.Get(index))
    apps.Start(ns.core.Seconds(0.0))
    apps.Stop(ns.core.Seconds(SIM_LENGTH))


def install_sink(topology: Topology, index: int) -> None:
    """install_sink

    install sink on a given node

    topology - the topology to install on
    index    - the node to install on
    """
    port = 9  # Discard port (RFC 863)
    sink = ns.applications.PacketSinkHelper(
        "ns3::UdpSocketFactory",
        ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo(),
    )
    apps = sink.Install(topology.nodes.Get(index))
    apps.Start(ns.core.Seconds(0.0))
    apps.Stop(ns.core.Seconds(SIM_LENGTH))


def update_topology() -> None:
    """update_topology

    update the topology
    """
    if GLOBAL_TOPOLOGY is None:
        return

    global GLOBAL_TIME  # pylint: disable=global-statement

    entities = get_stats(GLOBAL_TIME)
    for entity in entities:
        id = entity["id"]  # pylint:disable=redefined-builtin
        if not entity["can_connect"]:
            # take down each interface starting from index 1 (index 0 is loopback)
            for i in range(1, get_num_devices(GLOBAL_TOPOLOGY.nodes, id)):
                set_down(GLOBAL_TOPOLOGY.nodes, id, i)
        else:
            # update the connections
            # TODO update error rate
            conns = {}
            for i, conn in enumerate(entity["connections"]):
                conns[conn["id"]] = ConnectionData(
                    connected=conn["connected"],
                    trans_time=conn["trans_time"],
                )
            for i in range(1, get_num_devices(GLOBAL_TOPOLOGY.nodes, id)):
                conn_id = get_netdevice_node_index(GLOBAL_TOPOLOGY.nodes, id, i)
                if conn_id in conns and conns[conn_id].connected:
                    set_up(GLOBAL_TOPOLOGY.nodes, id, i)
                    set_channel_delay(
                        GLOBAL_TOPOLOGY.nodes, id, i, conns[conn_id].trans_time
                    )
                else:
                    set_down(GLOBAL_TOPOLOGY.nodes, id, i)

    # recompute routing tables and update time
    ns.internet.Ipv4GlobalRoutingHelper.RecomputeRoutingTables()
    GLOBAL_TIME += TIME_STEP


def map_interfaces(topology: Topology):
    interface_map = []
    for i in range(topology.num_nodes):
        for j in range(1, get_num_devices(topology.nodes, i)):
            interface_map.append([i, j, get_netdevice_node_index(topology.nodes, i, j)])

    return interface_map


def simulate() -> None:
    """simulate

    run a simulation
    """
    global GLOBAL_TOPOLOGY  # pylint: disable=global-statement

    # setup routing recomputation
    ns.Config.SetDefault(
        "ns3::Ipv4GlobalRouting::RespondToInterfaceEvents", ns.core.BooleanValue(True)
    )

    # init logging
    ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
    ns.core.LogComponentEnable("PacketSink", ns.core.LOG_LEVEL_INFO)

    # initial the topology
    topology = create_topology()
    GLOBAL_TOPOLOGY = topology
    install_onoff_app(topology, 1, 1, 5)
    install_sink(topology, 5)
    cpp_update_topology()

    # schedule recomputation of topology once a minute
    ns.core.Simulator.Schedule(ns.core.Seconds(60.0), cpp_update_topology)

    print_routing_table()

    interface_map = map_interfaces(topology)
    with open("interface_mapping.csv", "w+") as im_csv:
        csv_writer = csv.writer(im_csv, delimiter=",")
        csv_writer.writerow(["Input Node", "Interface", "Output Node"])
        csv_writer.writerows(interface_map)

    # run the simulator
    ns.core.Simulator.Run()
    ns.core.Simulator.Destroy()


if __name__ == "__main__":
    simulate()
