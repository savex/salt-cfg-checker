"""
Module to handle interaction with salt
"""
import os
import requests
import time

from cfg_checker.common import logger, config


def list_to_target_string(node_list, separator):
    result = ''
    for node in node_list:
        result += node + ' ' + separator + ' '
    return result[:-(len(separator)+2)]


class SaltRest(object):
    _host = config.salt_host
    _port = config.salt_port
    uri = "http://" + config.salt_host + ":" + config.salt_port
    _auth = {}

    default_headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Auth-Token': None
    }

    def __init__(self):
        self._token = self._login()
        self.last_response = None

    def get(self, path='', headers=default_headers, cookies=None):
        _path = os.path.join(self.uri, path)
        logger.debug("GET '{}'\nHeaders: '{}'\nCookies: {}".format(
            _path,
            headers,
            cookies
        ))
        return requests.get(
            _path,
            headers=headers,
            cookies=cookies
        )

    def post(self, data, path='', headers=default_headers, cookies=None):
        if data is None:
            data = {}
        _path = os.path.join(self.uri, path)
        if path == 'login':
            _data = str(data).replace(config.salt_pass, "*****")
        else:
            _data = data
        logger.debug("POST '{}'\nHeaders: '{}'\nCookies: {}\nBody: {}".format(
            _path,
            headers,
            cookies,
            _data
        ))
        return requests.post(
            os.path.join(self.uri, path),
            headers=headers,
            json=data,
            cookies=cookies
        )

    def _login(self):
        login_payload = {
            'username': config.salt_user,
            'password': config.salt_pass,
            'eauth': 'pam'
        }

        logger.debug("Logging in to salt master...")
        _response = self.post(login_payload, path='login')

        if _response.ok:
            self._auth['response'] = _response.json()['return'][0]
            self._auth['cookies'] = _response.cookies
            self.default_headers['X-Auth-Token'] = \
                self._auth['response']['token']
            return self._auth['response']['token']
        else:
            raise EnvironmentError(
                "HTTP:{}, Not authorized?".format(_response.status_code)
            )

    def salt_request(self, fn, *args, **kwargs):
        # if token will expire in 5 min, re-login
        if self._auth['response']['expire'] < time.time() + 300:
            self._auth['response']['X-Auth-Token'] = self._login()

        _method = getattr(self, fn)
        _response = _method(*args, **kwargs)
        self.last_response = _response
        _content = "..."
        _len = len(_response.content)
        if _len < 1024:
            _content = _response.content
        logger.debug(
            "Response (HTTP {}/{}), {}: {}".format(
                _response.status_code,
                _response.reason,
                _len,
                _content
            )
        )
        if _response.ok:
            return _response.json()['return']
        else:
            raise EnvironmentError(
                "Salt Error: HTTP:{}, '{}'".format(
                    _response.status_code,
                    _response.reason
                )
            )


class SaltRemote(SaltRest):
    def __init__(self):
        super(SaltRemote, self).__init__()

    def cmd(
            self,
            tgt,
            fun,
            param=None,
            client='local',
            kwarg=None,
            expr_form=None,
            tgt_type=None,
            timeout=None
    ):
        _timeout = timeout if timeout is not None else config.salt_timeout
        _payload = {
            'fun': fun,
            'tgt': tgt,
            'client': client,
            'timeout': _timeout
        }

        if expr_form:
            _payload['expr_form'] = expr_form
        if tgt_type:
            _payload['tgt_type'] = tgt_type
        if param:
            _payload['arg'] = param
        if kwarg:
            _payload['kwarg'] = kwarg

        _response = self.salt_request('post', [_payload])
        if isinstance(_response, list):
            return _response[0]
        else:
            raise EnvironmentError(
                "Unexpected response from from salt-api/LocalClient: "
                "{}".format(_response)
            )

    def run(self, fun, kwarg=None):
        _payload = {
            'client': 'runner',
            'fun': fun,
            'timeout': config.salt_timeout
        }

        if kwarg:
            _payload['kwarg'] = kwarg

        _response = self.salt_request('post', [_payload])
        if isinstance(_response, list):
            return _response[0]
        else:
            raise EnvironmentError(
                "Unexpected response from from salt-api/RunnerClient: "
                "{}".format(_response)
            )

    def wheel(self, fun, arg=None, kwarg=None):
        _payload = {
            'client': 'wheel',
            'fun': fun,
            'timeout': config.salt_timeout
        }

        if arg:
            _payload['arg'] = arg
        if kwarg:
            _payload['kwarg'] = kwarg

        _response = self.salt_request('post', _payload)['data']
        if _response['success']:
            return _response
        else:
            raise EnvironmentError(
                "Salt Error: '{}'".format(_response['return']))

    def pillar_request(self, node_target, pillar_submodule, argument):
        # example cli: 'salt "ctl01*" pillar.keys rsyslog'
        _type = "compound"
        if isinstance(node_target, list):
            _type = "list"
        return self.cmd(
            node_target,
            "pillar." + pillar_submodule,
            argument,
            expr_form=_type
        )

    def pillar_keys(self, node_target, argument):
        return self.pillar_request(node_target, 'keys', argument)

    def pillar_get(self, node_target, argument):
        return self.pillar_request(node_target, 'get', argument)

    def pillar_data(self, node_target, argument):
        return self.pillar_request(node_target, 'data', argument)

    def pillar_raw(self, node_target, argument):
        return self.pillar_request(node_target, 'raw', argument)

    def list_minions(self):
        """
            Fails in salt version 2016.3.8
            api returns dict of minions with grains
        """
        return self.salt_request('get', 'minions')

    def list_keys(self):
        """
            Fails in salt version 2016.3.8
            api should return dict:
            {
                'local': [],
                'minions': [],
                'minions_denied': [],
                'minions_pre': [],
                'minions_rejected': [],
            }
        """
        return self.salt_request('get', path='keys')

    def get_status(self):
        """
            'runner' client is the equivalent of 'salt-run'
            Returns the
        """
        return self.run(
            'manage.status',
            kwarg={'timeout': 10}
        )

    def get_active_nodes(self):
        if config.skip_nodes:
            logger.info("Nodes to be skipped: {0}".format(config.skip_nodes))
            return self.cmd(
                '* and not ' + list_to_target_string(
                    config.skip_nodes,
                    'and not'
                ),
                'test.ping',
                expr_form='compound')
        else:
            return self.cmd('*', 'test.ping')

    def get_monitoring_ip(self, param_name):
        salt_output = self.cmd(
            'docker:client:stack:monitoring',
            'pillar.get',
            param=param_name,
            expr_form='pillar')
        return salt_output[salt_output.keys()[0]]

    def f_touch_master(self, path, makedirs=True):
        _kwarg = {
            "makedirs": makedirs
        }
        salt_output = self.cmd(
            "cfg01*",
            "file.touch",
            param=path,
            kwarg=_kwarg
        )
        return salt_output[salt_output.keys()[0]]

    def f_append_master(self, path, strings_list, makedirs=True):
        _kwarg = {
            "makedirs": makedirs
        }
        _args = [path]
        _args.extend(strings_list)
        salt_output = self.cmd(
            "cfg01*",
            "file.write",
            param=_args,
            kwarg=_kwarg
        )
        return salt_output[salt_output.keys()[0]]

    def mkdir(self, target, path, tgt_type=None):
        salt_output = self.cmd(
            target,
            "file.mkdir",
            param=path,
            expr_form=tgt_type
        )
        return salt_output

    def f_manage_file(self, target_path, source,
                      sfn='', ret='{}',
                      source_hash={},
                      user='root', group='root', backup_mode='755',
                      show_diff='base',
                      contents='', makedirs=True):
        """
        REST variation of file.get_managed
        CLI execution goes like this (10 agrs):
        salt cfg01\* file.manage_file /root/test_scripts/pkg_versions.py
        '' '{}' /root/diff_pkg_version.py
        '{hash_type: 'md5', 'hsum': <md5sum>}' root root '755' base ''
        makedirs=True
            param: name - target file placement when managed
            param: source - source for the file
        """
        _source_hash = {
            "hash_type": "md5",
            "hsum": 000
        }
        _arg = [
            target_path,
            sfn,
            ret,
            source,
            _source_hash,
            user,
            group,
            backup_mode,
            show_diff,
            contents
        ]
        _kwarg = {
            "makedirs": makedirs
        }
        salt_output = self.cmd(
            "cfg01*",
            "file.manage_file",
            param=_arg,
            kwarg=_kwarg
        )
        return salt_output[salt_output.keys()[0]]

    def cache_file(self, target, source_path):
        salt_output = self.cmd(
            target,
            "cp.cache_file",
            param=source_path
        )
        return salt_output[salt_output.keys()[0]]

    def get_file(self, target, source_path, target_path, tgt_type=None):
        return self.cmd(
            target,
            "cp.get_file",
            param=[source_path, target_path],
            expr_form=tgt_type
        )

    @staticmethod
    def compound_string_from_list(nodes_list):
        return " or ".join(nodes_list)
