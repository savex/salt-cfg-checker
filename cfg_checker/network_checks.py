import json
import os
import sys

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
        logger_cli.info("-> Done collecting networks data")

        return

    def print_network_report(self):
        """
        Create text report for CLI

        :return: none
        """
        
        return
    
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
