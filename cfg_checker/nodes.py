import json
import os
from copy import deepcopy

from cfg_checker.clients import get_salt_remote, salt
from cfg_checker.common import config
from cfg_checker.common.const import all_roles_map
from cfg_checker.common.const import NODE_UP, NODE_DOWN, NODE_SKIP
from cfg_checker.common import logger, logger_cli
from cfg_checker.common import utils
from cfg_checker.common.exception import SaltException
from cfg_checker.common.settings import pkg_dir

node_tmpl = {
    'role': '',
    'node_group': '',
    'status': NODE_DOWN,
    'pillars': {},
    'grains': {}
}


class SaltNodes(object):
    def __init__(self):
        logger_cli.info("# Gathering environment information")
        # simple salt rest client
        self.salt = salt
        self.nodes = None

    def gather_node_info(self, skip_list, skip_list_file):
        # Keys for all nodes
        # this is not working in scope of 2016.8.3, will overide with list
        logger_cli.debug("... collecting node names existing in the cloud")
        if not self.salt:
            self.salt = get_salt_remote(config)

        try:
            _keys = self.salt.list_keys()
            _str = []
            for _k, _v in _keys.items():
                _str.append("{}: {}".format(_k, len(_v)))
            logger_cli.info("-> keys collected: {}".format(", ".join(_str)))

            self.node_keys = {
                'minions': _keys['minions']
            }
        except Exception:
            _keys = None
            self.node_keys = None

        # List of minions with grains
        _minions = self.salt.list_minions()
        if _minions:
            logger_cli.info(
                "-> api reported {} active minions".format(len(_minions))
            )
        elif not self.node_keys:
            # this is the last resort
            _minions = config.load_nodes_list()
            logger_cli.info(
                "-> {} nodes loaded from list file".format(len(_minions))
            )
        else:
            _minions = self.node_keys['minions']

        # Skip nodes if needed
        _skipped_minions = []
        # skip list file
        if skip_list_file:
            _valid, _invalid = utils.get_nodes_list(skip_list_file)
            logger_cli.info(
                "\n# WARNING: Detected invalid entries "
                "in nodes skip list:\n".format(
                    "\n".join(_invalid)
                )
            )
            _skipped_minions.extend(_valid)
        # process wildcard, create node list out of mask
        if skip_list:
            _list = []
            _invalid = []
            for _item in skip_list:
                if '*' in _item:
                    _str = _item[:_item.index('*')]
                    _nodes = [_m for _m in _minions if _m.startswith(_str)]
                    if not _nodes:
                        logger_cli.warn(
                            "# WARNING: No nodes found for {}".format(_item)
                        )
                    _list.extend(_nodes)
                else:
                    if _item in _minions:
                        _list += _item
                    else:
                        logger_cli.warn(
                            "# WARNING: No node found for {}".format(_item)
                        )
            # removing duplicates
            _list = list(set(_list))
            _skipped_minions.extend(_list)

        # in case API not listed minions, we need all that answer ping
        _active = self.salt.get_active_nodes()
        logger_cli.info("-> nodes responded: {}".format(len(_active)))
        # iterate through all accepted nodes and create a dict for it
        self.nodes = {}
        self.skip_list = []
        _domains = set()
        for _name in _minions:
            _nc = utils.get_node_code(_name)
            _rmap = all_roles_map
            _role = _rmap[_nc] if _nc in _rmap else 'unknown'
            if _name in _skipped_minions:
                _status = NODE_SKIP
                self.skip_list.append(_name)
            else:
                _status = NODE_UP if _name in _active else NODE_DOWN
                if _status == NODE_DOWN:
                    self.skip_list.append(_name)
                    logger_cli.info(
                        "-> '{}' is down, "
                        "added to skip list".format(
                            _name
                        )
                    )
            self.nodes[_name] = deepcopy(node_tmpl)
            self.nodes[_name]['shortname'] = _name.split(".", 1)[0]
            _domains.add(_name.split(".", 1)[1])
            self.nodes[_name]['node_group'] = _nc
            self.nodes[_name]['role'] = _role
            self.nodes[_name]['status'] = _status
        _domains = list(_domains)
        if len(_domains) > 1:
            logger_cli.warning(
                "Multiple domains detected: {}".format(",".join(_domains))
            )
        else:
            self.domain = _domains[0]
        logger_cli.info("-> {} nodes inactive".format(len(self.skip_list)))
        logger_cli.info("-> {} nodes collected".format(len(self.nodes)))

        # form an all nodes compound string to use in salt
        self.active_nodes_compound = self.salt.compound_string_from_list(
            filter(
                lambda nd: self.nodes[nd]['status'] == NODE_UP,
                self.nodes
            )
        )
        # get master node fqdn
        # _filtered = filter(
        #     lambda nd: self.nodes[nd]['role'] == const.all_roles_map['cfg'],
        #     self.nodes
        # )
        _role = all_roles_map['cfg']
        _filtered = [n for n, v in self.nodes.items() if v['role'] == _role]
        if len(_filtered) < 1:
            raise SaltException(
                "No master node detected! Check/Update node role map."
            )
        else:
            self.salt.master_node = _filtered[0]

        # OpenStack versions
        self.mcp_release = self.salt.pillar_get(
            self.salt.master_node,
            "_param:apt_mk_version"
        )[self.salt.master_node]
        self.openstack_release = self.salt.pillar_get(
            self.salt.master_node,
            "_param:openstack_version"
        )[self.salt.master_node]
        # Preload codenames
        # do additional queries to get linux codename and arch for each node
        self.get_specific_pillar_for_nodes("_param:linux_system_codename")
        self.get_specific_pillar_for_nodes("_param:linux_system_architecture")
        for _name in self.nodes.keys():
            _n = self.nodes[_name]
            if _name not in self.skip_list:
                _p = _n['pillars']['_param']
                _n['linux_codename'] = _p['linux_system_codename']
                _n['linux_arch'] = _p['linux_system_architecture']

    def skip_node(self, node):
        # Add node to skip list
        # Fro example if it is fails to comply with the rules

        # check if we know such node
        if node in self.nodes.keys() and node not in self.skip_list:
            # yes, add it
            self.skip_list.append(node)
            return True
        else:
            return False

    def get_nodes(self, skip_list=None, skip_list_file=None):
        if not self.nodes:
            if not skip_list and config.skip_nodes:
                self.gather_node_info(config.skip_nodes, skip_list_file)
            else:
                self.gather_node_info(skip_list, skip_list_file)
        return self.nodes

    def get_info(self):
        _info = {
           'mcp_release': self.mcp_release,
           'openstack_release': self.openstack_release
        }
        return _info

    def get_cmd_for_nodes(self, cmd, target_key, target_dict=None, nodes=None):
        """Function runs. cmd.run and parses result into place
        or into dict structure provided

        :return: no return value, data pulished internally
        """
        logger_cli.debug(
            "... collecting results for '{}'".format(cmd)
        )
        if target_dict:
            _nodes = target_dict
        else:
            _nodes = self.nodes
        _result = self.execute_cmd_on_active_nodes(cmd, nodes=nodes)
        for node, data in _nodes.items():

            if node in self.skip_list:
                logger_cli.debug(
                    "... '{}' skipped while collecting '{}'".format(
                        node,
                        cmd
                    )
                )
                continue
            # Prepare target key
            if target_key not in data:
                data[target_key] = None
            # Save data
            if data['status'] in [NODE_DOWN, NODE_SKIP]:
                data[target_key] = None
            elif node not in _result:
                continue
            elif not _result[node]:
                logger_cli.debug(
                    "... '{}' not responded after '{}'".format(
                        node,
                        config.salt_timeout
                    )
                )
                data[target_key] = None
            else:
                data[target_key] = _result[node]

    def get_specific_pillar_for_nodes(self, pillar_path):
        """Function gets pillars on given path for all nodes

        :return: no return value, data pulished internally
        """
        logger_cli.debug(
            "... collecting node pillars for '{}'".format(pillar_path)
        )
        _result = self.salt.pillar_get(self.active_nodes_compound, pillar_path)
        self.not_responded = []
        for node, data in self.nodes.items():
            if node in self.skip_list:
                logger_cli.debug(
                    "... '{}' skipped while collecting '{}'".format(
                        node,
                        pillar_path
                    )
                )
                continue
            _pillar_keys = pillar_path.split(':')
            _data = data['pillars']
            # pre-create nested dict
            for idx in range(0, len(_pillar_keys)-1):
                _key = _pillar_keys[idx]
                if _key not in _data:
                    _data[_key] = {}
                _data = _data[_key]
            if data['status'] in [NODE_DOWN, NODE_SKIP]:
                _data[_pillar_keys[-1]] = None
            elif not _result[node]:
                logger_cli.debug(
                    "... '{}' not responded after '{}'".format(
                        node,
                        config.salt_timeout
                    )
                )
                _data[_pillar_keys[-1]] = None
                self.not_responded.append(node)
            else:
                _data[_pillar_keys[-1]] = _result[node]

    def prepare_json_on_node(self, node, _dict, filename):
        # this function assumes that all folders are created
        _dumps = json.dumps(_dict, indent=2).splitlines()
        _storage_path = os.path.join(
            config.salt_file_root, config.salt_scripts_folder
        )
        logger_cli.debug(
            "... uploading data as '{}' "
            "to master's file cache folder: '{}'".format(
                filename,
                _storage_path
            )
        )
        _cache_path = os.path.join(_storage_path, filename)
        _source_path = os.path.join(
            'salt://',
            config.salt_scripts_folder,
            filename
        )
        _target_path = os.path.join(
            '/root',
            config.salt_scripts_folder,
            filename
        )

        logger_cli.debug("... creating file in cache '{}'".format(_cache_path))
        self.salt.f_touch_master(_cache_path)
        self.salt.f_append_master(_cache_path, _dumps)
        logger.debug("... syncing file to '{}'".format(node))
        self.salt.get_file(
            node,
            _source_path,
            _target_path,
            tgt_type="compound"
        )
        return _target_path

    def prepare_script_on_active_nodes(self, script_filename):
        # Prepare script
        _p = os.path.join(pkg_dir, 'scripts', script_filename)
        with open(_p, 'rt') as fd:
            _script = fd.read().splitlines()
        _storage_path = os.path.join(
            config.salt_file_root, config.salt_scripts_folder
        )
        logger_cli.debug(
            "... uploading script {} "
            "to master's file cache folder: '{}'".format(
                script_filename,
                _storage_path
            )
        )
        self.salt.mkdir(self.salt.master_node, _storage_path)
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

        logger_cli.debug("... creating file in cache '{}'".format(_cache_path))
        self.salt.f_touch_master(_cache_path)
        self.salt.f_append_master(_cache_path, _script)
        # command salt to copy file to minions
        logger_cli.debug(
            "... creating script target folder '{}'".format(
                _cache_path
            )
        )
        self.salt.mkdir(
            self.active_nodes_compound,
            os.path.join(
                '/root',
                config.salt_scripts_folder
            ),
            tgt_type="compound"
        )
        logger.debug("... syncing file to nodes")
        self.salt.get_file(
            self.active_nodes_compound,
            _source_path,
            _target_path,
            tgt_type="compound"
        )
        # return path on nodes, just in case
        return _target_path

    def execute_script_on_node(self, node, script_filename, args=[]):
        # Prepare path
        _target_path = os.path.join(
            '/root',
            config.salt_scripts_folder,
            script_filename
        )

        # execute script
        logger.debug("... running script on '{}'".format(node))
        # handle results for each node
        _script_arguments = " ".join(args) if args else ""
        self.not_responded = []
        _r = self.salt.cmd(
            node,
            'cmd.run',
            param='python {} {}'.format(_target_path, _script_arguments),
            expr_form="compound"
        )

        # all false returns means that there is no response
        self.not_responded = [_n for _n in _r.keys() if not _r[_n]]
        return _r

    def execute_script_on_active_nodes(self, script_filename, args=[]):
        # Prepare path
        _target_path = os.path.join(
            '/root',
            config.salt_scripts_folder,
            script_filename
        )

        # execute script
        logger_cli.debug("... running script")
        # handle results for each node
        _script_arguments = " ".join(args) if args else ""
        self.not_responded = []
        _r = self.salt.cmd(
            self.active_nodes_compound,
            'cmd.run',
            param='python {} {}'.format(_target_path, _script_arguments),
            expr_form="compound"
        )

        # all false returns means that there is no response
        self.not_responded = [_n for _n in _r.keys() if not _r[_n]]
        return _r

    def execute_cmd_on_active_nodes(self, cmd, nodes=None):
        # execute cmd
        self.not_responded = []
        _r = self.salt.cmd(
            nodes if nodes else self.active_nodes_compound,
            'cmd.run',
            param=cmd,
            expr_form="compound"
        )

        # all false returns means that there is no response
        self.not_responded = [_n for _n in _r.keys() if not _r[_n]]
        return _r

    def is_node_available(self, node, log=True):
        if node in self.skip_list:
            if log:
                logger_cli.info("-> node '{}' not active".format(node))
            return False
        elif node in self.not_responded:
            if log:
                logger_cli.info("-> node '{}' not responded".format(node))
            return False
        else:
            return True


salt_master = SaltNodes()
