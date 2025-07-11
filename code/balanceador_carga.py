from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import arp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet.packet import Packet


class LoadBalancer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    virtual_ip = "10.0.0.10"
    H5_mac = "00:00:00:00:00:05"
    H5_ip = "10.0.0.5"
    H6_mac = "00:00:00:00:00:06"
    H6_ip = "10.0.0.6"
    next_server = ""
    current_server = ""
    ip_to_port = {H5_ip: 5, H6_ip: 6}
    ip_to_mac = {
        "10.0.0.1": "00:00:00:00:00:01",
        "10.0.0.2": "00:00:00:00:00:02",
        "10.0.0.3": "00:00:00:00:00:03",
        "10.0.0.4": "00:00:00:00:00:04"
    }

    def __init__(self, *args, **kwargs):
        super(LoadBalancer, self).__init__(*args, **kwargs)
        self.next_server = self.H5_ip
        self.current_server = self.H5_ip

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Instala fluxo de table-miss para garantir Packet-In
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        dst = eth.dst
        src = eth.src

        print(f"Pacote recebido: src={src}, dst={dst}, porta de entrada={in_port}")

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.add_flow(datapath, pkt, parser, ofp, in_port)
            self.arp_response(datapath, pkt, eth, parser, ofp, in_port)
            self.current_server = self.next_server
            return

        if dst in self.ip_to_port:
            actions = [parser.OFPActionOutput(self.ip_to_port[dst])]
            out = parser.OFPPacketOut(datapath=datapath,
                                      buffer_id=msg.buffer_id,
                                      in_port=in_port,
                                      actions=actions,
                                      data=msg.data)
            datapath.send_msg(out)

    def arp_response(self, datapath, packet, eth, parser, ofp, in_port):
        arp_pkt = packet.get_protocol(arp.arp)
        dst_ip = arp_pkt.src_ip
        src_ip = arp_pkt.dst_ip
        dst_mac = eth.src

        if dst_ip not in [self.H5_ip, self.H6_ip]:
            if self.next_server == self.H5_ip:
                src_mac = self.H5_mac
                self.next_server = self.H6_ip
            else:
                src_mac = self.H6_mac
                self.next_server = self.H5_ip
        else:
            src_mac = self.ip_to_mac.get(src_ip, "00:00:00:00:00:00")

        e = ethernet.ethernet(dst_mac, src_mac, ether_types.ETH_TYPE_ARP)
        a = arp.arp(opcode=2, src_mac=src_mac, src_ip=src_ip,
                    dst_mac=dst_mac, dst_ip=dst_ip)
        p = Packet()
        p.add_protocol(e)
        p.add_protocol(a)
        p.serialize()

        actions = [parser.OFPActionOutput(ofp.OFPP_IN_PORT)]
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofp.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=p.data
        )
        datapath.send_msg(out)

    def add_flow(self, datapath, packet, parser, ofp, in_port):
        src_ip = packet.get_protocol(arp.arp).src_ip

        if src_ip in [self.H5_ip, self.H6_ip]:
            return

        match = parser.OFPMatch(in_port=in_port,
                                eth_type=0x0800,
                                ipv4_dst=self.virtual_ip)
        actions = [parser.OFPActionSetField(ipv4_dst=self.current_server),
                   parser.OFPActionOutput(self.ip_to_port[self.current_server])]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=1,
            buffer_id=ofp.OFP_NO_BUFFER,
            match=match,
            instructions=inst)
        datapath.send_msg(mod)

        match = parser.OFPMatch(in_port=self.ip_to_port[self.current_server],
                                eth_type=0x0800,
                                ipv4_src=self.current_server,
                                ipv4_dst=src_ip)
        actions = [parser.OFPActionSetField(ipv4_src=self.virtual_ip),
                   parser.OFPActionOutput(in_port)]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=1,
            buffer_id=ofp.OFP_NO_BUFFER,
            match=match,
            instructions=inst)
        datapath.send_msg(mod)