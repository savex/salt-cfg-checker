import os
import re

from check_versions.common.const import all_roles_map

from check_versions.common.exception import ConfigException

PKG_DIR = os.path.dirname(__file__)
PKG_DIR = os.path.join(PKG_DIR, os.pardir, os.pardir)
PKG_DIR = os.path.normpath(PKG_DIR)


class Utils(object):
    @staticmethod
    def validate_name(fqdn, message=False):
        """
        Function that tries to validate node name.
        Checks if code contains letters, has '.' in it,
        roles map contains code's role

        :param fqdn: node FQDN name to supply for the check
        :param message: True if validate should return error check message
        :return: False if checks failed, True if all checks passed
        """
        _message = "Validation passed"

        def _result():
            return (True, _message) if message else True

        # node role code checks
        _code = re.findall("[a-zA-Z]+", fqdn.split('.')[0])
        if len(_code) > 0:
            if _code[0] in all_roles_map:
                return _result()
            else:
                # log warning here
                _message = "Node code is unknown, '{}'. " \
                           "Please, update map".format(_code)
        else:
            # log warning here
            _message = "Node name is invalid, '{}'".format(fqdn)

        # put other checks here

        # output result
        return _result()

    @staticmethod
    def node_string_to_list(node_string):
        # supplied var should contain node list
        # if there is no ',' -> use space as a delimiter
        if node_string is not None:
            if node_string.find(',') < 0:
                return node_string.split(' ')
            else:
                return node_string.split(',')
        else:
            return []

    def get_node_code(self, fqdn):
        # validate
        _isvalid, _message = self.validate_name(fqdn, message=True)
        _code = re.findall("[a-zA-Z]+", fqdn.split('.')[0])
        # check if it is valid and raise if not
        if _isvalid:
            return _code[0]
        else:
            raise ConfigException(_message)

    def get_nodes_list(self, env, nodes_list):
        _list = []
        if env is None:
            # nothing supplied, use the one in repo
            try:
                with open(os.path.join(PKG_DIR, nodes_list)) as _f:
                    _list.extend(_f.read().splitlines())
            except IOError as e:
                raise ConfigException("Error while loading file, '{}': "
                                      "{}".format(e.filename, e.strerror))
        else:
            _list.extend(self.node_string_to_list(env))

        # validate names
        _invalid = []
        _valid = []
        for idx in range(len(_list)):
            _name = _list[idx]
            if not self.validate_name(_name):
                _invalid.append(_name)
            else:
                _valid.append(_name)

        return _valid


utils = Utils()
