import ipaddress
import json
from copy import deepcopy

from cfg_checker.common import logger_cli
from cfg_checker.common.exception import InvalidReturnException
from cfg_checker.modules.network.network_errors import NetworkErrors
from cfg_checker.nodes import salt_master

# TODO: use templated approach
# net interface structure should be the same
_if_item = {
    "name": "unnamed interface",
    "mac": "",
    "routes": {},
    "proto": "",
    "ip": [],
    "parameters": {}
}

# collection of configurations
_network_item = {
    "runtime": {},
    "config": {},
    "reclass": {}
}


class NetworkMapper(object):
    RECLASS = "reclass"
    CONFIG = "config"
    RUNTIME = "runtime"

    def __init__(
        self,
        errors_class=None,
        skip_list=None,
        skip_list_file=None
    ):
        logger_cli.info("# Initializing mapper")
        # init networks and nodes
        self.networks = {}
        self.nodes = salt_master.get_nodes(
            skip_list=skip_list,
            skip_list_file=skip_list_file
        )
        self.cluster = salt_master.get_info()
        self.domain = salt_master.domain
        # init and pre-populate interfaces
        self.interfaces = {k: {} for k in self.nodes}
        # Init errors class
        if errors_class:
            self.errors = errors_class
        else:
            logger_cli.debug("... init error logs folder")
            self.errors = NetworkErrors()

    def prepare_all_maps(self):
        self.map_network(self.RECLASS)
        self.map_network(self.RUNTIME)
        self.map_network(self.CONFIG)

    # adding net data to tree
    def _add_data(self, _list, _n, _h, _d):
        if _n not in _list:
            _list[_n] = {}
            _list[_n][_h] = [_d]
        elif _h not in _list[_n]:
            # there is no such host, just create it
            _list[_n][_h] = [_d]
        else:
            # there is such host... this is an error
            self.errors.add_error(
                self.errors.NET_DUPLICATE_IF,
                host=_h,
                dup_if=_d['name']
            )
            _list[_n][_h].append(_d)

    # TODO: refactor map creation. Build one map instead of two separate
    def _map_network_for_host(self, host, if_class, net_list, data):
        # filter networks for this IF IP
        _nets = [n for n in net_list.keys() if if_class.ip in n]
        _masks = [n.netmask for n in _nets]
        if len(_nets) > 1:
            # There a multiple network found for this IP, Error
            self.errors.add_error(
                self.errors.NET_SUBNET_INTERSECT,
                host=host,
                ip=str(if_class.exploded),
                networks="; ".join([str(_n) for _n in _nets])
            )
        # check mask match
        if len(_nets) > 0 and if_class.netmask not in _masks:
            self.errors.add_error(
                self.errors.NET_MASK_MISMATCH,
                host=host,
                if_name=data['name'],
                if_cidr=if_class.exploded,
                if_mapped_networks=", ".join([str(_n) for _n in _nets])
            )

        if len(_nets) < 1:
            self._add_data(net_list, if_class.network, host, data)
        else:
            # add all data
            for net in _nets:
                self._add_data(net_list, net, host, data)

        return net_list

    def _map_reclass_networks(self):
        # class uses nodes from self.nodes dict
        _reclass = {}
        # Get required pillars
        salt_master.get_specific_pillar_for_nodes("linux:network")
        for node in salt_master.nodes.keys():
            # check if this node
            if not salt_master.is_node_available(node):
                continue
            # get the reclass value
            _pillar = salt_master.nodes[node]['pillars']['linux']['network']
            # we should be ready if there is no interface in reclass for a node
            # for example on APT node
            if 'interface' in _pillar:
                _pillar = _pillar['interface']
            else:
                logger_cli.info(
                    "... node '{}' skipped, no IF section in reclass".format(
                        node
                    )
                )
                continue

            # build map based on IPs and save info too
            for if_name, _dat in _pillar.items():
                # get proper IF name
                _if_name = if_name if 'name' not in _dat else _dat['name']
                # place it
                if _if_name not in self.interfaces[node]:
                    self.interfaces[node][_if_name] = deepcopy(_network_item)
                self.interfaces[node][_if_name]['reclass'] = deepcopy(_dat)
                # map network if any
                if 'address' in _dat:
                    _if = ipaddress.IPv4Interface(
                        _dat['address'] + '/' + _dat['netmask']
                    )
                    _dat['name'] = _if_name
                    _dat['ifs'] = [_if]

                    _reclass = self._map_network_for_host(
                        node,
                        _if,
                        _reclass,
                        _dat
                    )

        return _reclass

    def _map_configured_networks(self):
        # class uses nodes from self.nodes dict
        _confs = {}

        # TODO: parse /etc/network/interfaces

        return _confs

    def _map_runtime_networks(self):
        # class uses nodes from self.nodes dict
        _runtime = {}
        logger_cli.info("# Mapping node runtime network data")
        salt_master.prepare_script_on_active_nodes("ifs_data.py")
        _result = salt_master.execute_script_on_active_nodes(
            "ifs_data.py",
            args=["json"]
        )
        for key in salt_master.nodes.keys():
            # check if we are to work with this node
            if not salt_master.is_node_available(key):
                continue
            # due to much data to be passed from salt_master,
            # it is happening in order
            if key in _result:
                _text = _result[key]
                if '{' in _text and '}' in _text:
                    _text = _text[_text.find('{'):]
                else:
                    raise InvalidReturnException(
                        "Non-json object returned: '{}'".format(
                            _text
                        )
                    )
                _dict = json.loads(_text[_text.find('{'):])
                salt_master.nodes[key]['routes'] = _dict.pop("routes")
                salt_master.nodes[key]['networks'] = _dict
            else:
                salt_master.nodes[key]['networks'] = {}
                salt_master.nodes[key]['routes'] = {}
            logger_cli.debug("... {} has {} networks".format(
                key,
                len(salt_master.nodes[key]['networks'].keys())
            ))
        logger_cli.info("-> done collecting networks data")

        logger_cli.info("-> mapping IPs")
        # match interfaces by IP subnets
        for host, node_data in salt_master.nodes.items():
            if not salt_master.is_node_available(host):
                continue

            for net_name, net_data in node_data['networks'].items():
                # cut net name
                _i = net_name.find('@')
                _name = net_name if _i < 0 else net_name[:_i]
                # get ips and calculate subnets
                if _name in ['lo']:
                    # skip the localhost
                    continue
                else:
                    # add collected data to interface storage
                    if _name not in self.interfaces[host]:
                        self.interfaces[host][_name] = \
                            deepcopy(_network_item)
                    self.interfaces[host][_name]['runtime'] = \
                        deepcopy(net_data)

                #  get data and make sure that wide mask goes first
                _ip4s = sorted(
                    net_data['ipv4'],
                    key=lambda s: s[s.index('/'):]
                )
                for _ip_str in _ip4s:
                    # create interface class
                    _if = ipaddress.IPv4Interface(_ip_str)
                    # check if this is a VIP
                    # ...all those will have /32 mask
                    net_data['vip'] = None
                    if _if.network.prefixlen == 32:
                        net_data['vip'] = str(_if.exploded)
                    if 'name' not in net_data:
                        net_data['name'] = _name
                    if 'ifs' not in net_data:
                        net_data['ifs'] = [_if]
                        # map it
                        _runtime = self._map_network_for_host(
                            host,
                            _if,
                            _runtime,
                            net_data
                        )
                    else:
                        # data is already there, just add VIP
                        net_data['ifs'].append(_if)

            def process_interface(lvl, interface, tree, res):
                # get childs for each root
                # tree row item (<if_name>, [<parents>], [<childs>])
                if lvl not in tree:
                    # - no level - add it
                    tree[lvl] = {}
                # there is such interface in this level?
                if interface not in tree[lvl]:
                    # - IF not present
                    _n = ''
                    if interface not in res:
                        _n = 'unknown IF'
                        _p = None
                        _c = None
                    else:
                        # -- get parents, add
                        _p = res[interface]['lower']
                        # -- get childs, add
                        _c = res[interface]['upper']

                    # if None, put empty list
                    _p = _p if _p else []
                    # if None, put empty list
                    _c = _c if _c else []
                    tree[lvl].update({
                        interface: {
                            "note": _n,
                            "parents": _p,
                            "children": _c,
                            "size": len(_p) if len(_p) > len(_c) else len(_c)
                        }
                    })
                    for p_if in tree[lvl][interface]["parents"]:
                        # -- cycle: execute process for next parent, lvl-1
                        process_interface(lvl-1, p_if, tree, res)
                    for c_if in tree[lvl][interface]["children"]:
                        # -- cycle: execute process for next child, lvl+1
                        process_interface(lvl+1, c_if, tree, res)
                else:
                    # - IF present - exit (been here already)
                    return

            def _put(cNet, cIndex, _list):
                _added = False
                _actual_index = -1
                # Check list len
                _len = len(_list)
                if cIndex >= _len:
                    # grow list to meet index
                    _list = _list + [''] * (cIndex - _len + 1)
                    _len = len(_list)

                for _cI in range(cIndex, _len):
                    # add child per index
                    # if space is free
                    if not _list[_cI]:
                        _list[_cI] = cNet
                        _added = True
                        _actual_index = _cI
                        break
                if not _added:
                    # grow list by one entry
                    _list = _list + [cNet]
                    _actual_index = len(_list) - 1
                return _actual_index, _list

            # build network hierachy
            nr = node_data['networks']
            # walk interface tree
            for _ifname in node_data['networks']:
                _tree = {}
                _level = 0
                process_interface(_level, _ifname, _tree, nr)
                # save tree for node/if
                node_data['networks'][_ifname]['tree'] = _tree

                # debug, print built tree
                # logger_cli.debug("# '{}'".format(_ifname))
                lvls = list(_tree.keys())
                lvls.sort()
                n = len(lvls)
                m = max([len(_tree[k].keys()) for k in _tree.keys()])
                matrix = [["" for i in range(m)] for j in range(n)]
                x = 0
                while True:
                    _lv = lvls.pop(0)
                    # get all interfaces on this level
                    nets = iter(_tree[_lv].keys())
                    while True:
                        y = 0
                        # get next interface
                        try:
                            _net = next(nets)
                        except StopIteration:
                            break
                        # all nets
                        _a = [_net]
                        # put current interface if this is only one left
                        if not _tree[_lv][_net]['children']:
                            if _net not in matrix[x]:
                                _, matrix[x] = _put(
                                    _net,
                                    y,
                                    matrix[x]
                                )
                            y += 1
                        else:
                            # get all nets with same child
                            for _c in _tree[_lv][_net]['children']:
                                for _o_net in nets:
                                    if _c in _tree[_lv][_o_net]['children']:
                                        _a.append(_o_net)
                                # flush collected nets
                                for idx in range(len(_a)):
                                    if _a[idx] in matrix[x]:
                                        # there is such interface on this level
                                        # get index
                                        _nI = matrix[x].index(_a[idx])
                                        _, matrix[x+1] = _put(
                                            _c,
                                            _nI,
                                            matrix[x+1]
                                        )
                                    else:
                                        # there is no such interface
                                        # add it
                                        _t, matrix[x] = _put(
                                            _a[idx],
                                            0,
                                            matrix[x]
                                        )
                                        # also, put child
                                        _, matrix[x+1] = _put(
                                            _c,
                                            _t,
                                            matrix[x+1]
                                        )
                                    # remove collected nets from processing
                                    if _a[idx] in nets:
                                        nets.remove(_a[idx])
                                y += len(_a)
                        if not nets:
                            x += 1
                            break
                    if not lvls:
                        break

                lines = []
                _columns = [len(max([i for i in li])) for li in matrix]
                for idx_y in range(m):
                    line = ""
                    for idx_x in range(n):
                        _len = _columns[idx_x] if _columns[idx_x] else 1
                        _fmt = "{" + ":{}".format(_len) + "} "
                        line += _fmt.format(matrix[idx_x][idx_y])
                    lines.append(line)
                node_data['networks'][_ifname]['matrix'] = matrix
                node_data['networks'][_ifname]['lines'] = lines
        return _runtime

    def map_network(self, source):
        # maps target network using given source
        _networks = None

        if source == self.RECLASS:
            _networks = self._map_reclass_networks()
        elif source == self.CONFIG:
            _networks = self._map_configured_networks()
        elif source == self.RUNTIME:
            _networks = self._map_runtime_networks()

        self.networks[source] = _networks
        return _networks

    def create_map(self):
        """Create all needed elements for map output

        :return: none
        """
        _runtime = self.networks[self.RUNTIME]
        _reclass = self.networks[self.RECLASS]

        # main networks, target vars
        _map = {}
        # No matter of proto, at least one IP will be present for the network
        # we interested in, since we are to make sure that L3 level
        # is configured according to reclass model
        for network in _reclass:
            # shortcuts
            _net = str(network)
            _map[_net] = {}
            if network not in _runtime:
                # reclass has network that not found in runtime
                self.errors.add_error(
                    self.errors.NET_NO_RUNTIME_NETWORK,
                    reclass_net=str(network)
                )
                logger_cli.warn(
                    "WARN: {}: {}".format(
                        " No runtime network ", str(network)
                    )
                )
                continue
            # hostnames
            names = sorted(_runtime[network].keys())
            for hostname in names:
                _notes = []
                node = hostname.split('.')[0]
                if not salt_master.is_node_available(hostname, log=False):
                    logger_cli.info(
                        "    {0:8} {1}".format(node, "node not available")
                    )
                    # add non-responsive node erorr
                    self.errors.add_error(
                        self.errors.NET_NODE_NON_RESPONSIVE,
                        host=hostname
                    )
                    _notes.append(
                        self.errors.get_error_type_text(
                            self.errors.NET_NODE_NON_RESPONSIVE
                        )
                    )
                    continue
                # lookup interface name on node using network CIDR
                _if_name = _runtime[network][hostname][0]["name"]
                _raw = self.interfaces[hostname][_if_name]['runtime']
                # get proper reclass
                _r = self.interfaces[hostname][_if_name]['reclass']
                _if_name_suffix = ""
                # get the proto value
                if _r:
                    _if_rc = ""
                else:
                    self.errors.add_error(
                        self.errors.NET_NODE_UNEXPECTED_IF,
                        host=hostname,
                        if_name=_if_name
                    )
                    _notes.append(
                        self.errors.get_error_type_text(
                            self.errors.NET_NODE_UNEXPECTED_IF
                        )
                    )
                    _if_rc = "*"

                if "proto" in _r:
                    _proto = _r['proto']
                else:
                    _proto = "-"

                if "type" in _r:
                    _if_name_suffix += _r["type"]
                if "use_interfaces" in _r:
                    _if_name_suffix += "->" + ",".join(_r["use_interfaces"])

                if _if_name_suffix:
                    _if_name_suffix = "({})".format(_if_name_suffix)

                # get gate and routes if proto is static
                if _proto == 'static':
                    # get the gateway for current net
                    _routes = salt_master.nodes[hostname]['routes']
                    _route = _routes[_net] if _net in _routes else None
                    # get the default gateway
                    if 'default' in _routes:
                        _d_gate = ipaddress.IPv4Address(
                            _routes['default']['gateway']
                        )
                    else:
                        _d_gate = None
                    _d_gate_str = str(_d_gate) if _d_gate else "No default!"
                    # match route with default
                    if not _route:
                        _gate = "?"
                    else:
                        _gate = _route['gateway'] if _route['gateway'] else "-"
                else:
                    # in case of manual and dhcp, no check possible
                    _gate = "-"
                    _d_gate = "-"
                    _d_gate_str = "-"
                # iterate through interfaces
                _a = _runtime[network][hostname]
                for _host in _a:
                    for _if in _host['ifs']:
                        _ip_str = str(_if.exploded)
                        _gate_error = ""
                        _up_error = ""
                        _mtu_error = ""

                        # Match gateway
                        if _proto == 'static':
                            # default reclass gate
                            _r_gate = "-"
                            if "gateway" in _r:
                                _r_gate = _r["gateway"]

                            # if values not match, put *
                            if _gate != _r_gate and _d_gate_str != _r_gate:
                                # if values not match, check if default match
                                self.errors.add_error(
                                    self.errors.NET_UNEXPECTED_GATEWAY,
                                    host=hostname,
                                    if_name=_if_name,
                                    ip=_ip_str,
                                    gateway=_gate
                                )
                                _notes.append(
                                    self.errors.get_error_type_text(
                                        self.errors.NET_UNEXPECTED_GATEWAY
                                    )
                                )
                                _gate_error = "*"

                        # IF status in reclass
                        _e = "enabled"
                        if _e not in _r:
                            self.errors.add_error(
                                self.errors.NET_NO_RC_IF_STATUS,
                                host=hostname,
                                if_name=_if_name
                            )
                            _notes.append(
                                self.errors.get_error_type_text(
                                    self.errors.NET_NO_RC_IF_STATUS
                                )
                            )
                            _up_error = "*"

                        _rc_mtu = _r['mtu'] if 'mtu' in _r else None
                        _rc_mtu_s = ""
                        # check if this is a VIP address
                        # no checks needed if yes.
                        if _host['vip'] != _ip_str:
                            if _rc_mtu:
                                _rc_mtu_s = str(_rc_mtu)
                                # if there is an MTU value, match it
                                if _host['mtu'] != _rc_mtu_s:
                                    self.errors.add_error(
                                        self.errors.NET_MTU_MISMATCH,
                                        host=hostname,
                                        if_name=_if_name,
                                        if_cidr=_ip_str,
                                        reclass_mtu=_rc_mtu,
                                        runtime_mtu=_host['mtu']
                                    )
                                    _notes.append(
                                        self.errors.get_error_type_text(
                                            self.errors.NET_MTU_MISMATCH
                                        )
                                    )
                                    _rc_mtu_s = "/" + _rc_mtu_s
                                    _mtu_error = "*"
                                else:
                                    # empty the matched value
                                    _rc_mtu_s = ""
                            elif _host['mtu'] != '1500' and \
                                    _proto not in ["-", "dhcp"]:
                                # there is no MTU value in reclass
                                # and runtime value is not default
                                self.errors.add_error(
                                    self.errors.NET_MTU_EMPTY,
                                    host=hostname,
                                    if_name=_if_name,
                                    if_cidr=_ip_str,
                                    if_mtu=_host['mtu']
                                )
                                _notes.append(
                                    self.errors.get_error_type_text(
                                        self.errors.NET_MTU_EMPTY
                                    )
                                )
                                _mtu_error = "*"
                        else:
                            # this is a VIP
                            _if_name = " "*7
                            _if_name_suffix = ""
                            _ip_str += " VIP"
                        # Save all data
                        _values = {
                            "interface": _if_name,
                            "interface_error": _if_rc,
                            "interface_note": _if_name_suffix,
                            "interface_map": "\n".join(_host['lines']),
                            "interface_matrix": _host['matrix'],
                            "ip_address": _ip_str,
                            "address_type": _proto,
                            "rt_mtu": _host['mtu'],
                            "rc_mtu": _rc_mtu_s,
                            "mtu_error": _mtu_error,
                            "status": _host['state'],
                            "status_error": _up_error,
                            "subnet_gateway": _gate,
                            "subnet_gateway_error": _gate_error,
                            "default_gateway": _d_gate_str,
                            "raw_data": _raw,
                            "error_note": " and ".join(_notes)
                        }
                        if node in _map[_net]:
                            # add if to host
                            _map[_net][node].append(_values)
                        else:
                            _map[_net][node] = [_values]
                        _notes = []

        # save map
        self.map = _map
        # other runtime networks found
        # docker, etc

        return

    def print_map(self):
        """
        Create text report for CLI

        :return: none
        """
        logger_cli.info("# Networks")
        logger_cli.info(
            "    {0:8} {1:25} {2:25} {3:6} {4:10} {5:10} {6}/{7}".format(
                "Host",
                "IF",
                "IP",
                "Proto",
                "MTU",
                "State",
                "Gate",
                "Def.Gate"
            )
        )
        for network in self.map.keys():
            logger_cli.info("-> {}".format(network))
            for hostname in self.map[network].keys():
                node = hostname.split('.')[0]
                _n = self.map[network][hostname]
                for _i in _n:
                    # Host IF IP Proto MTU State Gate Def.Gate
                    _text = "{:7} {:17} {:25} {:6} {:10} " \
                            "{:10} {} / {}".format(
                                _i['interface'] + _i['interface_error'],
                                _i['interface_note'],
                                _i['ip_address'],
                                _i['address_type'],
                                _i['rt_mtu'] + _i['rc_mtu'] + _i['mtu_error'],
                                _i['status'] + _i['status_error'],
                                _i['subnet_gateway'] +
                                _i['subnet_gateway_error'],
                                _i['default_gateway']
                            )
                    logger_cli.info(
                        "    {0:8} {1}".format(
                            node,
                            _text
                        )
                    )

        # logger_cli.info("\n# Other networks")
        # _other = [n for n in _runtime if n not in _reclass]
        # for network in _other:
        #     logger_cli.info("-> {}".format(str(network)))
        #     names = sorted(_runtime[network].keys())

        #     for hostname in names:
        #         for _n in _runtime[network][hostname]:
        #             _ifs = [str(ifs.ip) for ifs in _n['ifs']]
        #             _text = "{:25} {:25} {:6} {:10} {}".format(
        #                 _n['name'],
        #                 ", ".join(_ifs),
        #                 "-",
        #                 _n['mtu'],
        #                 _n['state']
        #             )
        #             logger_cli.info(
        #                 "    {0:8} {1}".format(hostname.split('.')[0], _text)
        #             )
        # logger_cli.info("\n")
