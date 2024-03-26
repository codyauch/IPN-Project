from ns import ns

ns.cppyy.cppdef("""
    using namespace ns3;

    NodeContainer create_node_pair(NodeContainer nodes, int i, int j) {
        return NodeContainer(nodes.Get(i), nodes.Get(j));
    }

    NodeContainer create_node_quad(NodeContainer nodes, int i, int j, int k, int l) {
        return NodeContainer(nodes.Get(i), nodes.Get(j), nodes.Get(k), nodes.Get(l));
    }

    void schedule_up_down(NodeContainer c) {
        Ptr<Node> n1 = c.Get(1);
        Ptr<Ipv4> ipv41 = n1->GetObject<Ipv4>();
        uint32_t ipv4ifIndex1 = 2;

        Simulator::Schedule(Seconds(2), &Ipv4::SetDown, ipv41, ipv4ifIndex1);
        Simulator::Schedule(Seconds(4), &Ipv4::SetUp, ipv41, ipv4ifIndex1);

        Ptr<Node> n6 = c.Get(6);
        Ptr<Ipv4> ipv46 = n6->GetObject<Ipv4>();
        uint32_t ipv4ifIndex6 = 2;
        Simulator::Schedule(Seconds(6), &Ipv4::SetDown, ipv46, ipv4ifIndex6);
        Simulator::Schedule(Seconds(8), &Ipv4::SetUp, ipv46, ipv4ifIndex6);

        Simulator::Schedule(Seconds(12), &Ipv4::SetDown, ipv41, ipv4ifIndex1);
        Simulator::Schedule(Seconds(14), &Ipv4::SetUp, ipv41, ipv4ifIndex1);
    }
    """
)

ns.Config.SetDefault("ns3::Ipv4GlobalRouting::RespondToInterfaceEvents", ns.core.BooleanValue(True))

ns.core.LogComponentEnable("OnOffApplication", ns.core.LOG_LEVEL_INFO)
ns.core.LogComponentEnable("PacketSink", ns.core.LOG_LEVEL_INFO)

c = ns.network.NodeContainer()
c.Create(7)
n0n2 = ns.cppyy.gbl.create_node_pair(c, 0, 2)
n1n2 = ns.cppyy.gbl.create_node_pair(c, 1, 2)
n5n6 = ns.cppyy.gbl.create_node_pair(c, 5, 6)
n1n6 = ns.cppyy.gbl.create_node_pair(c, 1, 6)
n2345 = ns.cppyy.gbl.create_node_quad(c, 2, 3, 4, 5)

internet = ns.internet.InternetStackHelper()
internet.Install(c)

# We create the channels first without any IP addressing information
p2p = ns.point_to_point.PointToPointHelper()
p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("5Mbps"))
p2p.SetChannelAttribute("Delay", ns.core.StringValue("2ms"))
d0d2 = p2p.Install(n0n2)
d1d6 = p2p.Install(n1n6)

d1d2 = p2p.Install(n1n2)

p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("5Mbps"))
p2p.SetChannelAttribute("Delay", ns.core.StringValue("10ms"))
d5d6 = p2p.Install(n5n6)

p2p.SetDeviceAttribute("DataRate", ns.core.StringValue("1500kbps"))
p2p.SetChannelAttribute("Delay", ns.core.StringValue("10ms"))
d5d6 = p2p.Install(n5n6)

# We create the channels first without any IP addressing information
csma = ns.csma.CsmaHelper()
csma.SetChannelAttribute("DataRate", ns.core.StringValue("5Mbps"))
csma.SetChannelAttribute("Delay", ns.core.StringValue("2ms"))
d2345 = csma.Install(n2345)

# Later, we add IP addresses
ipv4 = ns.internet.Ipv4AddressHelper()
ipv4.SetBase("10.1.1.0", "255.255.255.0")
ipv4.Assign(d0d2)

ipv4.SetBase("10.1.2.0", "255.255.255.0")
ipv4.Assign(d1d2)

ipv4.SetBase("10.1.3.0", "255.255.255.0")
i5i6 = ipv4.Assign(d5d6)

ipv4.SetBase("10.250.1.0", "255.255.255.0")
ipv4.Assign(d2345)

ipv4.SetBase("172.16.1.0", "255.255.255.0")
i1i6 = ipv4.Assign(d1d6)

# Create router nodes, initialize routing database and set up the routing tables in the nodes
ns.internet.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

# Create the OnOff application to send UDP datagrams of size 210 bytes at a rate of 448 Kb/s
port = 9 # Discard port (RFC 863)
onoff = ns.applications.OnOffHelper("ns3::UdpSocketFactory", ns.network.InetSocketAddress(i5i6.GetAddress(1), port).ConvertTo())
onoff.SetConstantRate(ns.network.DataRate("2kbps"))
onoff.SetAttribute("PacketSize", ns.core.UintegerValue(50))

apps = onoff.Install(c.Get(1))
apps.Start(ns.core.Seconds(1.0))
apps.Stop(ns.core.Seconds(10.0))

# Create a second OnOff application to send UDP datagrams of size 210 bytes at a rate of 448 Kb/s
onoff2 = ns.applications.OnOffHelper("ns3::UdpSocketFactory", ns.network.InetSocketAddress(i1i6.GetAddress(1), port).ConvertTo())
onoff2.SetAttribute("OnTime", ns.core.StringValue("ns3::ConstantRandomVariable[Constant=1]"))
onoff2.SetAttribute("OffTime", ns.core.StringValue("ns3::ConstantRandomVariable[Constant=0]"))
onoff2.SetAttribute("DataRate", ns.core.StringValue("2kbps"))
onoff2.SetAttribute("PacketSize", ns.core.UintegerValue(50))

apps2 = onoff2.Install(c.Get(1))
apps2.Start(ns.core.Seconds(11.0))
apps2.Stop(ns.core.Seconds(16.0))

# Create an optional packet sink to receive these packets
sink = ns.applications.PacketSinkHelper("ns3::UdpSocketFactory", ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo())
apps = sink.Install(c.Get(6))
apps.Start(ns.core.Seconds(1.0))
apps.Stop(ns.core.Seconds(10.0))

sink2 = ns.applications.PacketSinkHelper("ns3::UdpSocketFactory", ns.InetSocketAddress(ns.Ipv4Address.GetAny(), port).ConvertTo())
apps2 = sink2.Install(c.Get(6))
apps2.Start(ns.core.Seconds(11.0))
apps2.Stop(ns.core.Seconds(16.0))

# let's skip the ascii stuff

# schedule stuff
ns.cppyy.gbl.schedule_up_down(c)

ns.core.Simulator.Run()
ns.core.Simulator.Destroy()
