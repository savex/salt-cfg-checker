import json
import os
import sys

from copy import deepcopy

import reporter

from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.common import salt_utils

node_tmpl = {
    'role': '',
    'node_group': '',
    'status': const.NODE_DOWN,
    'pillars': {},
    'grains': {}
}


class CloudPackageChecker(object):
    def __init__(self):
        logger_cli.info("### Collecting nodes for package check")
        # simple salt rest client
        self.salt = salt_utils.SaltRemote()

        # Keys for all nodes
        # this is not working in scope of 2016.8.3, will overide with list
        # cls.node_keys = cls.salt.list_keys()

        logger_cli.info("### Collecting node names existing in the cloud")
        self.node_keys = {
            'minions': config.all_nodes
        }

        # all that answer ping
        _active = self.salt.get_active_nodes()
        logger_cli.debug("-> Nodes responded: {}".format(_active))
        # just inventory for faster interaction
        # iterate through all accepted nodes and create a dict for it
        self.nodes = {}
        for _name in self.node_keys['minions']:
            _nc = utils.get_node_code(_name)
            _rmap = const.all_roles_map
            _role = _rmap[_nc] if _nc in _rmap else 'unknown'
            _status = const.NODE_UP if _name in _active else const.NODE_DOWN

            self.nodes[_name] = deepcopy(node_tmpl)
            self.nodes[_name]['node_group'] = _nc
            self.nodes[_name]['role'] = _role
            self.nodes[_name]['status'] = _status

        logger_cli.info("-> {} nodes collected".format(len(self.nodes)))

    def collect_installed_packages(self):
        """
        Collect installed packages on each node
        sets 'installed' dict property in the class

        :return: none
        """
        logger_cli.info("### Collecting installed packages")
        # form an all nodes compound string to use in salt
        _active_nodes_string = self.salt.compound_string_from_list(
            filter(
                lambda nd: self.nodes[nd]['status'] == const.NODE_UP,
                self.nodes
            )
        )
        # Prepare script
        _script_filename = "pkg_versions.py"
        _p = os.path.join(pkg_dir, 'scripts', _script_filename)
        with open(_p, 'rt') as fd:
            _script = fd.read().splitlines()
        _storage_path = os.path.join(
            config.salt_file_root, config.salt_scripts_folder
        )
        logger_cli.debug(
            "# Uploading script {} to master's file cache folder: '{}'".format(
                _script_filename,
                _storage_path
            )
        )
        _result = self.salt.mkdir("cfg01*", _storage_path)
        # Form cache, source and target path
        _cache_path = os.path.join(_storage_path, _script_filename)
        _source_path = os.path.join(
            'salt://',
            config.salt_scripts_folder,
            _script_filename
        )
        _target_path = os.path.join(
            '/root',
            config.salt_scripts_folder,
            _script_filename
        )

        logger_cli.debug("# Creating file in cache '{}'".format(_cache_path))
        _result = self.salt.f_touch_master(_cache_path)
        _result = self.salt.f_append_master(_cache_path, _script)
        # command salt to copy file to minions
        logger_cli.debug("# Creating script target folder '{}'".format(_cache_path))
        _result = self.salt.mkdir(
            _active_nodes_string,
            os.path.join(
                '/root',
                config.salt_scripts_folder
            ),
            tgt_type="compound"
        )
        logger_cli.info("-> Running script to all active nodes")
        _result = self.salt.get_file(
            _active_nodes_string,
            _source_path,
            _target_path,
            tgt_type="compound"
        )
        # execute pkg collecting script
        logger.debug("Running script to all nodes")
        # handle results for each node
        _result = self.salt.cmd(
            _active_nodes_string,
            'cmd.run',
            param='python {}'.format(_target_path),
            expr_form="compound"
        )
        for key in self.nodes.keys():
            # due to much data to be passed from salt, it is happening in order
            if key in _result:
                _text = _result[key]
                _dict = json.loads(_text[_text.find('{'):])
                self.nodes[key]['packages'] = _dict
            else:
                self.nodes[key]['packages'] = {}
            logger_cli.debug("# {} has {} packages installed".format(
                key,
                len(self.nodes[key]['packages'].keys())
            ))
        logger_cli.info("-> Done")

    def collect_packages(self):
        """
        Check package versions in repos vs installed

        :return: no return values, all date put to dict in place
        """
        _all_packages = {}
        for node_name, node_value in self.nodes.iteritems():
            for package_name in node_value['packages']:
                if package_name not in _all_packages:
                    _all_packages[package_name] = {}
                _all_packages[package_name][node_name] = node_value

        # TODO: process data for per-package basis

        self.all_packages = _all_packages

    def create_html_report(self, filename):
        """
        Create static html showing packages diff per node

        :return: buff with html
        """
        logger_cli.info("### Generating report to '{}'".format(filename))
        _report = reporter.ReportToFile(
            reporter.HTMLPackageCandidates(),
            filename
        )
        _report({
            "nodes": self.nodes,
            "diffs": {}
        })
        logger_cli.info("-> Done")


if __name__ == '__main__':
    # init connection to salt and collect minion data
    cl = CloudPackageChecker()

    # collect data on installed packages
    cl.collect_installed_packages()

    # diff installed and candidates
    # cl.collect_packages()

    # report it
    cl.create_html_report("./pkg_versions.html")

    sys.exit(0)
