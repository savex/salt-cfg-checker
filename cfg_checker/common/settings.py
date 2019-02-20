import os

from exception import ConfigException
from log import logger
from other import utils

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.join(pkg_dir, os.pardir, os.pardir)
pkg_dir = os.path.normpath(pkg_dir)
pkg_dir = os.path.abspath(pkg_dir)

_default_work_folder = os.path.normpath(pkg_dir)


class CheckerConfiguration(object):
    def _init_values(self):
        """Load values from environment variables or put default ones
        """

        self.name = "CheckerConfig"
        self.working_folder = os.environ.get(
            'CFG_TESTS_WORK_DIR',
            _default_work_folder
        )
        self.date_format = "%Y-%m-%d %H:%M:%S.%f%z"
        self.default_tz = "UTC"

        self.salt_host = os.environ.get('SALT_URL', None)
        self.salt_port = os.environ.get('SALT_PORT', '6969')
        self.salt_user = os.environ.get('SALT_USER', 'salt')
        self.salt_pass = os.environ.get('SALT_PASSWORD', None)
        self.salt_timeout = os.environ.get('SALT_TIMEOUT', 30)
        self.salt_file_root = os.environ.get('SALT_FILE_ROOT', None)
        self.salt_scripts_folder = os.environ.get(
            'SALT_SCRIPTS_FOLDER',
            'cfg_checker_scripts'
        )
        self.all_nodes = utils.get_nodes_list(
            os.environ.get('CFG_ALL_NODES', None),
            os.environ.get('SALT_NODE_LIST_FILE', None)
        )
        self.skip_nodes = utils.node_string_to_list(os.environ.get(
            'CFG_SKIP_NODES',
            None
        ))

    @staticmethod
    def _init_env(env_name=None):
        """[summary]

        Keyword Arguments:
            env_name {str} -- environment name to search configuration
                files in etc/<env_name>.env (default: {None})

        Raises:
            ConfigException -- on IO error when loading env file
            ConfigException -- on env file failed validation
        """
        # load env file as init os.environment with its values
        if env_name is None:
            _env_name = 'default'
        else:
            _env_name = env_name
        _config_path = os.path.join(pkg_dir, 'etc', _env_name + '.env')
        if os.path.isfile(_config_path):
            with open(_config_path) as _f:
                _list = _f.read().splitlines()
            logger.debug("Loading env vars from '{}'".format(_config_path))
        else:
            raise ConfigException(
                "Failed to load enviroment vars from '{}'".format(
                    _config_path
                )
            )
        for index in range(len(_list)):
            _line = _list[index]
            # skip comments
            if _line.strip().startswith('#'):
                continue
            # validate
            _errors = []
            if _line.find('=') < 0 or _line.count('=') > 1:
                _errors.append("Line {}: {}".format(index, _line))
            else:
                # save values
                _t = _line.split('=')
                _key, _value = _t[0], _t[1]
                os.environ[_key] = _value
        # if there was errors, report them
        if _errors:
            raise ConfigException(
                "Environment file failed validation in lines: {}".format(
                    "\n".join(_errors)
                )
            )
        else:
            logger.debug("Loaded total of '{}' vars".format(len(_list)))

    def __init__(self):
        """Base configuration class. Only values that are common for all scripts
        """
        _env = os.getenv('SALT_ENV', None)
        self._init_env(_env)
        self._init_values()


config = CheckerConfiguration()
