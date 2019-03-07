import json
import os
import sys

from  copy import deepcopy

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


class SaltNodes(object):
    def __init__(self):
        logger_cli.info("### Collecting nodes")
        # simple salt rest client
        self.salt = salt_utils.SaltRemote()

        # Keys for all nodes
        # this is not working in scope of 2016.8.3, will overide with list
        logger_cli.info("# Collecting node names existing in the cloud")
        try:
            _keys = self.salt.list_keys()
            _str = []
            for _k, _v in _keys.iteritems():
                _str.append("{}: {}".format(_k, len(_v)))
            logger_cli.info("-> keys collected: {}".format(", ".join(_str)))

            self.node_keys = {
                'minions': _keys['minions']
            }
        except Exception as e:
            _keys = None
            self.node_keys = None
        
        # List of minions with grains
        _minions = self.salt.list_minions()
        if _minions:
            logger_cli.info("-> api reported {} active minions".format(len(_minions)))
        elif not self.node_keys:
            # this is the last resort
            _minions = config.load_nodes_list()
            logger_cli.info("-> {} nodes loaded from list file".format(len(_minions)))
        else:
            _minions = self.node_keys['minions']

        # in case API not listed minions, we need all that answer ping
        _active = self.salt.get_active_nodes()
        logger_cli.info("-> nodes responded: {}".format(len(_active)))
        # just inventory for faster interaction
        # iterate through all accepted nodes and create a dict for it
        self.nodes = {}
        for _name in _minions:
            _nc = utils.get_node_code(_name)
            _rmap = const.all_roles_map
            _role = _rmap[_nc] if _nc in _rmap else 'unknown'
            _status = const.NODE_UP if _name in _active else const.NODE_DOWN

            self.nodes[_name] = deepcopy(node_tmpl)
            self.nodes[_name]['node_group'] = _nc
            self.nodes[_name]['role'] = _role
            self.nodes[_name]['status'] = _status

        logger_cli.info("-> {} nodes collected".format(len(self.nodes)))

        # form an all nodes compound string to use in salt
        self.active_nodes_compound = self.salt.compound_string_from_list(
            filter(
                lambda nd: self.nodes[nd]['status'] == const.NODE_UP,
                self.nodes
            )
        )

    def get_nodes(self):
        return self.nodes

    def get_specific_pillar_for_nodes(self, pillar_path):
        """Function gets pillars on given path for all nodes

        :return: no return value, data pulished internally
        """
        logger_cli.info("# Collecting node pillars for '{}'".format(pillar_path))
        _result = self.salt.pillar_get(self.active_nodes_compound, pillar_path)
        for node, data in self.nodes.iteritems():
            _pillar_keys = pillar_path.split(':')
            _data = data['pillars']
            # pre-create nested dict
            for idx in range(0, len(_pillar_keys)-1):
                _key = _pillar_keys[idx]
                if _key not in _data:
                    _data[_key] = {}
                _data = _data[_key]
            _data[_pillar_keys[-1]] = _result[node]
    
    def execute_script_on_active_nodes(self, script_filename, args=[]):
        # Prepare script
        _p = os.path.join(pkg_dir, 'scripts', script_filename)
        with open(_p, 'rt') as fd:
            _script = fd.read().splitlines()
        _storage_path = os.path.join(
            config.salt_file_root, config.salt_scripts_folder
        )
        logger_cli.debug(
            "# Uploading script {} to master's file cache folder: '{}'".format(
                script_filename,
                _storage_path
            )
        )
        _result = self.salt.mkdir("cfg01*", _storage_path)
        # Form cache, source and target path
        _cache_path = os.path.join(_storage_path, script_filename)
        _source_path = os.path.join(
            'salt://',
            config.salt_scripts_folder,
            script_filename
        )
        _target_path = os.path.join(
            '/root',
            config.salt_scripts_folder,
            script_filename
        )

        logger_cli.debug("# Creating file in cache '{}'".format(_cache_path))
        _result = self.salt.f_touch_master(_cache_path)
        _result = self.salt.f_append_master(_cache_path, _script)
        # command salt to copy file to minions
        logger_cli.debug("# Creating script target folder '{}'".format(_cache_path))
        _result = self.salt.mkdir(
            self.active_nodes_compound,
            os.path.join(
                '/root',
                config.salt_scripts_folder
            ),
            tgt_type="compound"
        )
        logger_cli.info("-> Running script to all active nodes")
        _result = self.salt.get_file(
            self.active_nodes_compound,
            _source_path,
            _target_path,
            tgt_type="compound"
        )
        # execute pkg collecting script
        logger.debug("Running script to all nodes")
        # handle results for each node
        _script_arguments = " ".join(args) if args else ""
        _result = self.salt.cmd(
            self.active_nodes_compound,
            'cmd.run',
            param='python {} {}'.format(_target_path, _script_arguments),
            expr_form="compound"
        )

        # TODO: Handle error result

        return _result
