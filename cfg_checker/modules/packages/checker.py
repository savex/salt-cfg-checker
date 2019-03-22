import json
import os
#import sys

from copy import deepcopy

from cfg_checker.reports import reporter
from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.common import salt_utils
from cfg_checker.nodes import SaltNodes, node_tmpl


class CloudPackageChecker(SaltNodes):
    def collect_installed_packages(self):
        """
        Collect installed packages on each node
        sets 'installed' dict property in the class

        :return: none
        """
        logger_cli.info("# Collecting installed packages")
        _result = self.execute_script_on_active_nodes("pkg_versions.py")

        for key in self.nodes.keys():
            # due to much data to be passed from salt, it is happening in order
            if key in _result:
                _text = _result[key]
                try:
                    _dict = json.loads(_text[_text.find('{'):])
                except ValueError as e:
                    logger_cli.info("... no JSON for '{}'".format(
                        key
                    ))
                    logger_cli.debug("ERROR:\n{}\n".format(_text[:_text.find('{')]))
                    _dict = {}
                
                self.nodes[key]['packages'] = _dict
            else:
                self.nodes[key]['packages'] = {}
            logger_cli.debug("... {} has {} packages installed".format(
                key,
                len(self.nodes[key]['packages'].keys())
            ))
        logger_cli.info("-> Done")

    def collect_packages(self):
        """
        Check package versions in repos vs installed

        :return: no return values, all date put to dict in place
        """
        # Collect packages from all of the nodes in flat dict
        _diff_packages = {}
        for node_name, node_value in self.nodes.iteritems():
            for _name, _value in node_value['packages'].iteritems():
                if _name not in _diff_packages:
                    _diff_packages[_name] = {}
                    _diff_packages[_name]['df_nodes'] = {}
                    _diff_packages[_name]['eq_nodes'] = []
                
                # compare packages, mark if equal
                if _value['installed'] != _value['candidate']:
                    # Saving compare value so we not do str compare again
                    _value['is_equal'] = False
                    # add node name to list
                    _diff_packages[_name]['df_nodes'][node_name] = {
                        'i': _value['installed'],
                        'c': _value['candidate'],
                        'raw': _value['raw']
                    }
                else:
                    # Saving compare value so we not do str compare again
                    _value['is_equal'] = True
                    _diff_packages[_name]['eq_nodes'].append(node_name)

        self.diff_packages = _diff_packages

    def create_html_report(self, filename):
        """
        Create static html showing packages diff per node

        :return: buff with html
        """
        logger_cli.info("# Generating report to '{}'".format(filename))
        _report = reporter.ReportToFile(
            reporter.HTMLPackageCandidates(),
            filename
        )
        _report({
            "nodes": self.nodes,
            "rc_diffs": {},
            "pkg_diffs": self.diff_packages
        })
        logger_cli.info("-> Done")
