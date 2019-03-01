import json
import os
import sys
import ipaddress

from copy import deepcopy

import reporter

from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.common import salt_utils
from cfg_checker.nodes import SaltNodes, node_tmpl


class NetworkChecker(SaltNodes):
    def collect_network_info(self):
        """
        Collects info on the network using ifs_data.py script

        :return: none
        """
        logger_cli.info("### Collecting network data")
        _result = self.execute_script("ifs_data.py", args=["json"])

        for key in self.nodes.keys():
            # due to much data to be passed from salt, it is happening in order
            if key in _result:
                _text = _result[key]
                _dict = json.loads(_text[_text.find('{'):])
                self.nodes[key]['networks'] = _dict
            else:
                self.nodes[key]['networks'] = {}
            logger_cli.debug("# {} has {} networks".format(
                key,
                len(self.nodes[key]['networks'].keys())
            ))
        logger_cli.info("-> done collecting networks data")

        # dump collected data to speed up coding
        # with open('dump.json', 'w+') as ff:
        #     ff.write(json.dumps(self.nodes))

        # load dump data
        # with open('dump.json', 'r') as ff:
        #     _nodes = json.loads(ff.read())

        logger_cli.info("### Building network tree")
        # match physical interfaces by MAC addresses
        _all_nets = {}
        for host, node_data in self.nodes.iteritems():
            for net_name, net_data in node_data['networks'].iteritems():
                # get ips and calculate subnets
                if net_name == 'lo':
                    continue
                _ip4s = net_data['ipv4']
                for _ip_str in _ip4s.keys():
                    _if = ipaddress.IPv4Interface(_ip_str)
                    if not any(_if.ip in net for net in _all_nets.keys()):
                        # IP not fits into existing networks
                        if _if.network not in _all_nets.keys():
                            _all_nets[_if.network] = {}
                        
                        _all_nets[_if.network][host] = {}
                        _all_nets[_if.network][host]['text'] = \
                                "{0:30}: {1:19} {2:5} {3:4}".format(
                                    net_name,
                                    str(_if.ip),
                                    net_data['mtu'],
                                    net_data['state']
                                )
                        _all_nets[_if.network][host]['if_data'] = net_data
                    else:
                        # There is a network that ip fits into
                        for _net in _all_nets.keys():
                            if _if.ip in _net:
                                if host not in _all_nets[_net]:
                                    _all_nets[_net][host] = {}
                                _all_nets[_net][host]['text'] = \
                                    "{0:30}: {1:19} {2:5} {3:4}".format(
                                        net_name,
                                        str(_if.ip),
                                        net_data['mtu'],
                                        net_data['state']
                                    )
                                _all_nets[_net][host]['if_data'] = \
                                    net_data

        # save collected info
        self.all_networks = _all_nets

        # Get networks from reclass
        # TODO: 

        return

    def print_network_report(self):
        """
        Create text report for CLI

        :return: none
        """
        for network, nodes in self.all_networks.iteritems():
            logger_cli.info("-> {}".format(str(network)))
            names = sorted(nodes.keys())

            for hostname in names:
                logger_cli.info(
                    "\t{0:10} {1}".format(
                        hostname.split('.')[0],
                        nodes[hostname]['text']
                    )
                )
    
    def create_html_report(self, filename):
        """
        Create static html showing network schema-like report

        :return: none
        """
        logger_cli.info("### Generating report to '{}'".format(filename))
        _report = reporter.ReportToFile(
            reporter.HTMLNetworkReport(),
            filename
        )
        _report({
            "nodes": self.nodes,
            "diffs": {}
        })
        logger_cli.info("-> Done")


if __name__ == '__main__':
    # init connection to salt and collect minion data
    cl = NetworkChecker()

    # collect data on installed packages
    cl.collect_network_info()

    # diff installed and candidates
    # cl.collect_packages()

    # report it
    cl.create_html_report("./pkg_versions.html")

    sys.exit(0)
