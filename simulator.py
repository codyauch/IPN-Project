#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation;
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

"""Run an interplanetary network simulation"""

import sys

try:
    from ns import ns
except ModuleNotFoundError:
    sys.exit(
        "Error: ns3 Python module not found;"
        " Python bindings may not be enabled"
        " or your PYTHONPATH might not be properly configured"
    )

# define C++ functions
# --------------------
ns.cppyy.cppdef("""
    using namespace ns3;

    void set_error_rate(NetDeviceContainer devices, int index, double rate, char *unit) {
        Ptr<RateErrorModel> em = CreateObject<RateErrorModel>();
        em->SetAttribute("ErrorRate", DoubleValue(rate));
        em->SetAttribute("ErrorUnit", StringValue(unit));
        devices.Get(1)->SetAttribute("ReceiveErrorModel", PointerValue(em));
    }
""")

class Client:
    """Client

    A class containing the various field needed to initialize an NS-3 client
    """
    def __init__(self, node, address, port: int):
        self.node = node
        self.address = address
        self.port = port
        self.max_packets = 1
        self.interval = 1.0
        self.packet_size = 1024

    def set_port(self, port):
        """set_port

        set the port that the client sends from
        """
        self.port = port

    def set_max_packets(self, max_packets: int):
        """set_max_packets

        set the maximum number of packets that this client will send
        """
        self.max_packets = max_packets

    def set_interval(self, interval: float):
        """set_interval

        set the interval between sending for this client
        """
        self.interval = interval

    def set_packet_size(self, packet_size: int):
        """set_packet_size

        set the packet size that this client sends
        """
        self.packet_size = packet_size

class Server: # pylint: disable=too-few-public-methods
    """Server

    A class containing the various field needed to initialize an NS-3 server
    """
    def __init__(self, node, port: int):
        self.node = node
        self.port = port

    def set_port(self, port):
        """set_port

        set the port that the client sends from
        """
        self.port = port

def logging_init():
    """logging_init

    initialize the logging components for each application type
    """
    ns.core.LogComponentEnable("UdpEchoClientApplication", ns.core.LOG_LEVEL_INFO)
    ns.core.LogComponentEnable("UdpEchoServerApplication", ns.core.LOG_LEVEL_INFO)

def channel_init(nodes, rate: str, delay: str, error_rate: float, error_unit: str):
    """channel_init

    create a channel with a specific rate, delay, and error rate

    nodes      - the nodes connected by this channel
    rate       - the rate that data is sent
    delay      - the time it takes for a message to reach its destination
    error_rate - the rate at which errors happen on [0,1]
    error_unit - the unit to apply the error rate at
    """
    point_to_point = ns.point_to_point.PointToPointHelper()
    point_to_point.SetDeviceAttribute("DataRate", ns.core.StringValue(rate))
    point_to_point.SetChannelAttribute("Delay", ns.core.StringValue(delay))

    devices = point_to_point.Install(nodes)
    ns.cppyy.gbl.set_error_rate(devices, 1, error_rate, error_unit)

    return devices

def setup_internet_stack(nodes, devices):
    """setup_internet_stack

    sets up internet protocols on the nodes and devices

    nodes   - the nodes on the network
    devices - the devices on the network
    """
    stack = ns.internet.InternetStackHelper()
    stack.Install(nodes)

    address = ns.internet.Ipv4AddressHelper()
    address.SetBase(ns.network.Ipv4Address("10.1.1.0"), ns.network.Ipv4Mask("255.255.255.0"))

    return address.Assign(devices)

def create_server(server: Server, start_time: float, stop_time: float):
    """create_server

    create a server to simulate

    server     - the server to create
    start_time - the time step that the server starts up
    stop_time  - the time step that the server stops
    """
    echo_server = ns.applications.UdpEchoServerHelper(server.port)

    server_apps = echo_server.Install(server.node)
    server_apps.Start(ns.core.Seconds(start_time))
    server_apps.Stop(ns.core.Seconds(stop_time))

def create_client(client: Client, start_time: float, stop_time: float):
    """create_client

    create a client to simulate

    client     - the client to create
    start_time - the time step that the client starts up
    stop_time  - the time step that the client stops
    """
    echo_client = ns.applications.UdpEchoClientHelper(client.address, client.port)
    echo_client.SetAttribute("MaxPackets", ns.core.UintegerValue(client.max_packets))
    echo_client.SetAttribute("Interval", ns.core.TimeValue(ns.core.Seconds(client.interval)))
    echo_client.SetAttribute("PacketSize", ns.core.UintegerValue(client.packet_size))

    client_apps = echo_client.Install(client.node)
    client_apps.Start(ns.core.Seconds(start_time))
    client_apps.Stop(ns.core.Seconds(stop_time))

def main():
    """main

    run the simulation
    """
    logging_init()

    # create the nodes
    nodes = ns.network.NodeContainer()
    nodes.Create(2)

    devices = channel_init(nodes, "5Mbps", "2ms", 0.5, "ERROR_UNIT_PACKET")

    interfaces = setup_internet_stack(nodes, devices)

    server = Server(nodes.Get(1), 9)
    create_server(server, 1.0, 10.0)

    client = Client(nodes.Get(0), interfaces.GetAddress(1).ConvertTo(), 9)
    client.set_max_packets(10)
    create_client(client, 2.0, 10.0)

    ns.core.Simulator.Run()
    ns.core.Simulator.Destroy()

if __name__=="__main__":
    main()
