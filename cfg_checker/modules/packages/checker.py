import json
import os
#import sys

from copy import deepcopy

from cfg_checker.common.exception import ConfigException
from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.common import salt_utils
from cfg_checker.helpers.console_utils import Progress
from cfg_checker.nodes import SaltNodes, node_tmpl
from cfg_checker.reports import reporter

from versions import PkgVersions, DebianVersion, VersionCmpResult


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
        # Preload OpenStack release versions
        _desc = PkgVersions()
        
        logger_cli.info("# Cross-comparing: Installed vs Candidates vs Release")
        _progress = Progress(len(self.nodes.keys()))
        _progress_index = 0
        # Collect packages from all of the nodes in flat dict
        _diff_packages = {}
        _all_packages = {}
        for node_name, node_value in self.nodes.iteritems():
            _uniq_len = len(_all_packages.keys())
            _progress_index += 1
            _progress.write_progress(
                _progress_index,
                note="/ {} uniq packages found".format(_uniq_len)
            )
            for _name, _value in node_value['packages'].iteritems():
                if _name == 'librbd1' and node_name == 'gtw01.us.intcloud.mirantis.net':
                    a = 1
                # Parse versions
                _ver_ins = DebianVersion(_value['installed'])
                _ver_can = DebianVersion(_value['candidate'])

                # All packages list with version and node list
                if _name not in _all_packages:
                    # shortcuts for this cloud values
                    _os = self.openstack_release
                    _mcp = self.mcp_release
                    _pkg_desc = {}
                    if _desc[_name]:
                        # shortcut to version library
                        _vers = _desc[_name]['versions']
                        _pkg_desc = _desc[_name]
                    else:
                        # no description - no library :)
                        _vers = {}
                        _pkg_desc = _desc.dummy_desc
                    
                    # get specific set for this OS release if present
                    if _os in _vers:
                        _v = _vers[_os] 
                    elif 'any' in _vers:
                        _v = _vers['any']
                    else:
                        _v = {}
                    # Finally, get specific version
                    _release = DebianVersion(_v[_mcp] if _mcp in _v else '')
                    # Populate package info
                    _all_packages[_name] = {
                        "desc": _pkg_desc,
                        "results": {},
                        "r": _release,
                    }
                
                # list with differences
                if _name not in _diff_packages:
                    _diff_packages[_name] = {}
                    _diff_packages[_name]['df_nodes'] = {}
                    _diff_packages[_name]['eq_nodes'] = []

                _cmp = VersionCmpResult(
                    _ver_ins,
                    _ver_can,
                    _all_packages[_name]['r']
                )
                
                # shortcut to results
                _res = _all_packages[_name]['results']
                # update status
                if _cmp.status not in _res:
                    _res[_cmp.status] = {}
                # update action
                if _cmp.action not in _res[_cmp.status]:
                    _res[_cmp.status][_cmp.action] = {}
                # update node
                if node_name not in _res[_cmp.status][_cmp.action]:
                    _res[_cmp.status][_cmp.action][node_name] = {}
                # put result
                _res[_cmp.status][_cmp.action][node_name] = {
                    'i': _ver_ins,
                    'c': _ver_can,
                    'res': _cmp,
                    'raw': _value['raw']
                }

                if _cmp.status != const.VERSION_OK:
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
        self.all_packages = _all_packages
        _progress.newline()

    def create_report(self, filename, rtype):
        """
        Create static html showing packages diff per node

        :return: buff with html
        """
        logger_cli.info("# Generating report to '{}'".format(filename))
        if rtype == 'html':
            _type = reporter.HTMLPackageCandidates()
        elif rtype == 'csv':
            _type = reporter.CSVAllPackages()
        else:
            raise ConfigException("Report type not set")
        _report = reporter.ReportToFile(
            _type,
            filename
        )
        _report({
            "nodes": self.nodes,
            "rc_diffs": {},
            "pkg_diffs": self.diff_packages,
            "all_pkg": self.all_packages,
            "mcp_release": self.mcp_release,
            "openstack_release": self.openstack_release
        })
        logger_cli.info("-> Done")
