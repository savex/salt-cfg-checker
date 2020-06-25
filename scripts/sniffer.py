import binascii
import socket
import struct


class unpack:
    def __init__(self):
        self.data = None

    # Ethernet Header
    def eth_header(self, data):
        storeobj = data
        storeobj = struct.unpack("!6s6sH", storeobj)
        destination_mac = binascii.hexlify(storeobj[0])
        source_mac = binascii.hexlify(storeobj[1])
        eth_protocol = storeobj[2]
        data = {"Destination Mac": destination_mac,
                "Source Mac": source_mac,
                "Protocol": eth_protocol}
        return data

    # ICMP HEADER Extraction
    def icmp_header(self, data):
        icmph = struct.unpack('!BBH', data)
        icmp_type = icmph[0]
        code = icmph[1]
        checksum = icmph[2]
        data = {'ICMP Type': icmp_type,
                "Code": code,
                "CheckSum": checksum}
        return data

    # UDP Header Extraction
    def udp_header(self, data):
        storeobj = struct.unpack('!HHHH', data)
        source_port = storeobj[0]
        dest_port = storeobj[1]
        length = storeobj[2]
        checksum = storeobj[3]
        data = {"Source Port": source_port,
                "Destination Port": dest_port,
                "Length": length,
                "CheckSum": checksum}
        return data

    # IP Header Extraction
    def ip_header(self, data):
        storeobj = struct.unpack("!BBHHHBBH4s4s", data)
        _version = storeobj[0]
        _tos = storeobj[1]
        _total_length = storeobj[2]
        _identification = storeobj[3]
        _fragment_Offset = storeobj[4]
        _ttl = storeobj[5]
        _protocol = storeobj[6]
        _header_checksum = storeobj[7]
        _source_address = socket.inet_ntoa(storeobj[8])
        _destination_address = socket.inet_ntoa(storeobj[9])

        data = {'Version': _version,
                "Tos": _tos,
                "Total Length": _total_length,
                "Identification": _identification,
                "Fragment": _fragment_Offset,
                "TTL": _ttl,
                "Protocol": _protocol,
                "Header CheckSum": _header_checksum,
                "Source Address": _source_address,
                "Destination Address": _destination_address}
        return data

    # Tcp Header Extraction
    def tcp_header(self, data):
        storeobj = struct.unpack('!HHLLBBHHH', data)
        _source_port = storeobj[0]
        _destination_port = storeobj[1]
        _sequence_number = storeobj[2]
        _acknowledge_number = storeobj[3]
        _offset_reserved = storeobj[4]
        _tcp_flag = storeobj[5]
        _window = storeobj[6]
        _checksum = storeobj[7]
        _urgent_pointer = storeobj[8]
        data = {"Source Port": _source_port,
                "Destination Port": _destination_port,
                "Sequence Number": _sequence_number,
                "Acknowledge Number": _acknowledge_number,
                "Offset & Reserved": _offset_reserved,
                "Tcp Flag": _tcp_flag,
                "Window": _window,
                "CheckSum": _checksum,
                "Urgent Pointer": _urgent_pointer
                }
        return data

# Mac Address Formating


def mac_formater(a):
    b = "%.2x:%.2x:%.2x:%.2x:%.2x:%.2x" % (ord(a[0]), ord(
        a[1]), ord(a[2]), ord(a[3]), ord(a[4]), ord(a[5]))
    return b


def get_host(q):
    try:
        k = socket.gethostbyaddr(q)
    except Exception:
        k = 'Unknown'
    return k


s = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0800))
u = unpack()
count = 32
while count > 0:
    count -= 1
    # Capture packets from network
    pkt = s.recvfrom(65565)

    print "\n\n=== [+] ------------ Ethernet Header----- [+]"

    # print data on terminal
    for i in u.eth_header(pkt[0][0:14]).items():
        a, b = i
        print "{} : {} | ".format(a, b),
    print "\n=== [+] ------------ IP Header ------------[+]"
    for i in u.ip_header(pkt[0][14:34]).items():
        a, b = i
        print "{} : {} | ".format(a, b),
    print "\n== [+] ------------ Tcp Header ----------- [+]"
    for i in u.tcp_header(pkt[0][34:54]).items():
        a, b = i
        print "{} : {} | ".format(a, b),
    print "\n===== Data ===="
    print pkt[0][54:]
    print "\n======="
    print pkt[1:]
