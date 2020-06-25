import ipaddress
import json

from cfg_checker.common import logger_cli
from cfg_checker.helpers.console_utils import Progress
from cfg_checker.modules.network.mapper import NetworkMapper
from cfg_checker.modules.network.network_errors import NetworkErrors
from cfg_checker.nodes import salt_master


# This is independent class with a salt.nodes input
class NetworkPinger(object):
    def __init__(
        self,
        mtu=None,
        detailed=False,
        errors_class=None,
        skip_list=None,
        skip_list_file=None
    ):
        logger_cli.info("# Initializing")
        # all active nodes in the cloud
        self.target_nodes = salt_master.get_nodes(
            skip_list=skip_list,
            skip_list_file=skip_list_file
        )

        # default MTU value
        self.target_mtu = mtu if mtu else 64
        # only data
        self.packet_size = int(self.target_mtu) - 20 - 8
        self.detailed_summary = detailed

        if errors_class:
            self.errors = errors_class
        else:
            logger_cli.debug("... init error logs folder")
            self.errors = NetworkErrors()

    def _collect_node_addresses(self, target_net):
        # use reclass model and standard methods
        # to create list of nodes with target network
        _mapper = NetworkMapper(errors_class=self.errors)
        _reclass = _mapper.map_network(_mapper.RUNTIME)
        if target_net in _reclass:
            return _reclass[target_net]
        else:
            logger_cli.info(
                "# Target network of {} not found in reclass".format(
                    target_net.exploded
                )
            )
            return None

    def ping_nodes(self, network_cidr_str):
        # Conduct actual ping using network CIDR
        logger_cli.info("# Collecting node pairs")
        _fake_if = ipaddress.IPv4Interface(str(network_cidr_str))
        _net = _fake_if.network
        # collect nodes and ips from reclass
        nodes = self._collect_node_addresses(_net)
        # build list of packets to be sent
        # source -> target
        _count = 0
        _packets = {}
        _nodes = sorted(nodes.keys())
        _nodes_total = len(_nodes)
        logger_cli.info("-> {} nodes found within subnet of '{}'".format(
            _nodes_total,
            network_cidr_str
        ))
        while len(_nodes) > 0:
            src_host = _nodes.pop()
            src_data = nodes[src_host]
            src_if_name = src_data[0]['name']
            src_ips = [str(_if.ip) for _if in src_data[0]['ifs']]
            _packets[src_host] = {
                "ip": src_ips[0],
                "if_name": src_if_name,
                "targets": {}
            }

            for tgt_host, tgt_data in nodes.items():
                _t = _packets[src_host]["targets"]
                for tgt_if in tgt_data:
                    tgt_if_name = tgt_if['name']
                    _ip_index = 0
                    for tgt_ip in tgt_if['ifs']:
                        _ip = str(tgt_ip.ip)
                        if _ip not in src_ips:
                            if tgt_host not in _t:
                                _t[tgt_host] = []
                            _tgt = {
                                "ip": _ip,
                                "tgt_host": tgt_host,
                                "ip_index": _ip_index,
                                "if_name": tgt_if_name,
                                "mtu": self.target_mtu,
                                "size": self.packet_size
                            }
                            _t[tgt_host].append(
                                _tgt
                            )
                            _count += 1
                            _ip_index += 1
                        else:
                            pass
        logger_cli.info("-> {} packets to send".format(_count))

        if not _count:
            logger_cli.warning(
                "\n# WARNING: No packets to send for '{}', "
                "check network configuration\n".format(network_cidr_str)
            )

            return -1

        # do ping of packets
        logger_cli.info("# Pinging nodes: MTU={}".format(self.target_mtu))
        salt_master.prepare_script_on_active_nodes("ping.py")
        _progress = Progress(_count)
        _progress_index = 0
        _node_index = 0
        for src, src_data in _packets.items():
            _targets = src_data["targets"]
            _node_index += 1
            # create 'targets.json' on source host
            _path = salt_master.prepare_json_on_node(
                src,
                _targets,
                "targets.json"
            )
            # execute ping.py
            _results = salt_master.execute_script_on_node(
                src,
                "ping.py",
                args=[_path]
            )
            _progress_index += len(_targets)
            # print progress
            _progress.write_progress(
                _progress_index,
                note='/ {}/{} nodes / current {}'.format(
                    _node_index,
                    _nodes_total,
                    src
                )
            )
            # Parse salt output
            _result = _results[src]
            try:
                _result = json.loads(_result)
            except (ValueError, TypeError):
                _progress.clearline()
                logger_cli.error(
                    "# ERROR: Unexpected salt return for '{}': '{}'\n".format(
                        src,
                        _result
                    )
                )
                self.errors.add_error(
                    self.errors.NET_NODE_NON_RESPONSIVE,
                    node=src,
                    response=_result
                )
                continue
            # Handle return codes
            for tgt_node, _tgt_ips in _result.items():
                for _params in _tgt_ips:
                    _body = "{}({}) --{}--> {}({}@{})\n".format(
                            src,
                            src_data["if_name"],
                            _params["returncode"],
                            tgt_node,
                            _params["if_name"],
                            _params["ip"]
                        )
                    _stdout = ""
                    _stderr = ""
                    if len(_params["stdout"]) > 0:
                        _stdout = "stdout:\n{}\n".format(_params["stdout"])
                    if len(_params["stderr"]) > 0:
                        _stderr = "stderr:\n{}\n".format(_params["stderr"])

                    if not _params["returncode"]:
                        # 0
                        self.errors.add_error(
                            self.errors.NET_PING_SUCCESS,
                            ping_path=_body,
                            stdout=_stdout,
                            stderr=_stderr
                        )
                    elif _params["returncode"] == 68:
                        # 68 is a 'can't resove host error'
                        self.errors.add_error(
                            self.errors.NET_PING_NOT_RESOLVED,
                            ping_path=_body,
                            stdout=_stdout,
                            stderr=_stderr
                        )
                    elif _params["returncode"] > 1:
                        # >1 is when no actial (any) response
                        self.errors.add_error(
                            self.errors.NET_PING_ERROR,
                            ping_path=_body,
                            stdout=_stdout,
                            stderr=_stderr
                        )
                    else:
                        # 1 is for timeouts amd/or packet lost
                        self.errors.add_error(
                            self.errors.NET_PING_TIMEOUT,
                            ping_path=_body,
                            stdout=_stdout,
                            stderr=_stderr
                        )

            # Parse results back in place
            src_data["targets"] = _result

        _progress.end()

        return 0

    def print_summary(self):
        logger_cli.info(self.errors.get_summary(print_zeros=False))

    def print_details(self):
        # Detailed errors
        logger_cli.info(
            "\n{}\n".format(
                self.errors.get_errors()
            )
        )
