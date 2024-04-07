from enum import Enum
import json
from ns import ns
from physics_simulation import get_stats

# NOTE ------------------------------------------------------------------------
# Multiply all times output by this by 26 to get the correct time
# This divider gets around the very limited TTL on sockets
# This is a workaround to not have to implement my own TCP protocol from scratch
# and guarantees that message sent across the diameter of Mars's orbit will not
# time out before they even arrive
TIME_DIVIDER = 26

ns.cppyy.cppdef(
    """
#include "CPyCppyy/API.h"

// There literally is not any other way to do this
// I hate having to call Python from C++, but c'est la vie
void cpp_update_topology() {
    CPyCppyy::Eval("update_topology()");
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

// set the delay on a channel
void set_channel_delay(NodeContainer c, int index, int interface, double seconds) {
    Ptr<Channel> ch = c.Get(index)->GetDevice(interface)->GetChannel();

    ch->SetAttribute("Delay", TimeValue(Seconds(seconds)));
}

// set the channel error
void set_channel_error(NodeContainer c, int index, int interface, double rate) {
    Ptr<NetDevice> ch = c.Get(index)->GetDevice(interface);
    Ptr<RateErrorModel> em = CreateObject<RateErrorModel>();
    em->SetAttribute("ErrorRate", DoubleValue(rate));
    em->SetUnit(RateErrorModel::ERROR_UNIT_BIT);

    ch->SetAttribute("ReceiveErrorModel", PointerValue(em));
}
    """
)

# C++ classes
NodeContainer = ns.cppyy.gbl.ns3.NodeContainer
NetDeviceContainer = ns.cppyy.gbl.ns3.NetDeviceContainer
Ipv4InterfaceContainer = ns.cppyy.gbl.ns3.Ipv4InterfaceContainer

# C++ functions
set_down = ns.cppyy.gbl.set_down
set_up = ns.cppyy.gbl.set_up
set_channel_delay = ns.cppyy.gbl.set_channel_delay
set_channel_error = ns.cppyy.gbl.set_channel_error


def update_topology():
    NETWORK.update_topology()


class Protocol(Enum):
    UDP = 1
    TCP = 2


class Network:
    def __init__(
        self,
        start_time: int,
        protocol: Protocol,
        sender_body: str,
        receiver_body: str,
        time_step: int = 60,
        simulation_len: int = 60 * 60 * 24,
    ) -> None:
        # assign instance variables
        self.time = start_time
        self.protocol = protocol
        self.time_step = time_step
        self.simulation_len = simulation_len

        # configure ns-3 options
        ns.Config.SetDefault(
            "ns3::Ipv4GlobalRouting::RespondToInterfaceEvents",
            ns.core.BooleanValue(True),
        )

        # setup tracing
        self.ascii = ns.network.AsciiTraceHelper()
        self.stream = self.ascii.CreateFileStream("network-sim.tr")

        # setup the network
        self.ipv4 = ns.internet.Ipv4AddressHelper()
        self.__create_nodes()
        self.__connect_routers()
        self.__connect_end_devices(sender_body, receiver_body)
        ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()
        self.__install_applications()

    def run(self):
        ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
        ns.core.LogComponentEnable("PacketSink", ns.core.LOG_LEVEL_INFO)

        global NETWORK
        NETWORK = self

        # schedule topology updates once per time step
        curr = self.time_step
        while curr < self.simulation_len:
            ns.core.Simulator.Schedule(
                ns.core.Seconds(curr), ns.cppyy.gbl.cpp_update_topology
            )
            curr += self.time_step

        ns.core.Simulator.Run()
        ns.core.Simulator.Destroy()

    def update_topology(self):
        entities = get_stats(self.time)

        for i in range(0, len(entities) - 1):
            connections = [-1] * len(entities)
            for i, conn in enumerate(entities[i]["connections"]):
                connections[conn["id"]] = i
            for j in range(i, len(entities)):
                # since j>i, we know that interface # is the same as id
                if connections[j] == -1:
                    set_down(self.routers, i, j)
                else:
                    details = entities[i]["connections"][connections[j]]
                    if details["connected"]:
                        set_channel_delay(
                            self.routers, i, j, details["trans_time"] / TIME_DIVIDER
                        )
                        # set_channel_delay(self.routers, i, j, 61.399)
                        set_channel_error(self.routers, i, j, details["error_rate"])
                        set_up(self.routers, i, j)
                    else:
                        set_down(self.routers, i, j)
        ns.internet.Ipv4GlobalRoutingHelper.RecomputeRoutingTables()
        self.time += self.time_step

    def __create_nodes(self):
        self.routers = ns.network.NodeContainer()
        self.sender = ns.network.NodeContainer()
        self.receiver = ns.network.NodeContainer()

        # map entity names to ids
        entities = get_stats(0)
        self.entity_name_map = {}
        e_id = 0
        for entity in entities:
            self.entity_name_map[entity["name"]] = e_id
            e_id += 1

        # create one router for each entity and two end devices
        self.num_routers = len(entities)
        self.routers.Create(self.num_routers)
        self.sender.Create(1)
        self.receiver.Create(1)

    def __connect_routers(self):
        p2p = ns.point_to_point.PointToPointHelper()
        p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("10Mbps"))
        p2p.SetChannelAttribute("Delay", ns.core.StringValue("10ms"))
        p2p.EnableAsciiAll(self.stream)

        self.ipv4.SetBase("10.0.0.0", "255.255.255.0")
        internet = ns.internet.InternetStackHelper()
        internet.Install(self.routers)

        for i in range(0, self.num_routers - 1):
            for j in range(1, self.num_routers):
                nd = p2p.Install(self.routers.Get(i), self.routers.Get(j))
                self.ipv4.Assign(nd)
        self.ipv4.NewNetwork()

    def __connect_end_devices(self, sender_body: str, receiver_body: str):
        sender_id = self.entity_name_map[sender_body]
        receiver_id = self.entity_name_map[receiver_body]

        # create a zero delay channel from an end device to its channel
        p2p = ns.point_to_point.PointToPointHelper()
        p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("10Mbps"))
        p2p.SetChannelAttribute("Delay", ns.core.StringValue("0ms"))
        p2p.EnableAsciiAll(self.stream)
        self.sender_to_router = p2p.Install(
            self.sender.Get(0), self.routers.Get(sender_id)
        )
        self.router_to_receiver = p2p.Install(
            self.routers.Get(receiver_id), self.receiver.Get(0)
        )

        # install internet stack on the end devices
        internet = ns.internet.InternetStackHelper()
        internet.Install(self.sender)
        internet.Install(self.receiver)
        self.sender_to_router_address = self.ipv4.Assign(self.sender_to_router)
        self.ipv4.NewNetwork()
        self.router_to_receiver_address = self.ipv4.Assign(self.router_to_receiver)

    def __install_applications(self):
        port = 9

        if self.protocol == Protocol.TCP:
            factory = "ns3::TcpSocketFactory"
        elif self.protocol == Protocol.UDP:
            factory = "ns3::UdpSocketFactory"
        else:
            return

        # create sender application
        onoff = ns.applications.OnOffHelper(
            factory,
            ns.network.InetSocketAddress(
                self.router_to_receiver_address.GetAddress(1), port
            ).ConvertTo(),
        )
        rate = 8 / self.time_step
        onoff.SetConstantRate(ns.network.DataRate(f"{rate}kbps"))
        onoff.SetAttribute("PacketSize", ns.core.UintegerValue(1024))
        apps_onoff = onoff.Install(self.sender.Get(0))
        apps_onoff.Start(ns.core.Seconds(1.0))
        apps_onoff.Stop(ns.core.Seconds(self.simulation_len))

        # create receiver application
        sink = ns.applications.PacketSinkHelper(
            factory,
            ns.network.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo(),
        )
        apps_sink = sink.Install(self.receiver.Get(0))
        apps_sink.Start(ns.core.Seconds(1.0))
        apps_sink.Stop(ns.core.Seconds(self.simulation_len))


network = Network(10000, Protocol.TCP, "Earth", "Mars", simulation_len=60 * 60 * 24)
network.run()
