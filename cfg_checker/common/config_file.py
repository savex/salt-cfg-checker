import configparser
import os

from . import logger_cli


class ConfigFile(object):
    _truth = ['true', '1', 't', 'y', 'yes', 'yeah', 'yup',
              'certainly', 'uh-huh']
    _config = None
    _section_name = None
    _config_filepath = None

    def __init__(self, section_name, filepath=None):
        self._section_name = section_name
        self._config = configparser.ConfigParser()
        if filepath is not None:
            self._config_filepath = self._ensure_abs_path(filepath)
            self._config.read(self._config_filepath)
        else:
            logger_cli.debug("... previous iteration conf not found")

    def force_reload_config(self, path):
        _path = self._ensure_abs_path(path)
        self._config.read(_path)

    def save_config(self, filepath=None):
        if filepath:
            self._config_filepath = filepath
        with open(self._config_filepath, "w") as configfile:
            self._config.write(configfile)

    @staticmethod
    def _ensure_abs_path(path):
        if path.startswith('~'):
            path = os.path.expanduser(path)
        else:
            # keep it safe, create var :)
            path = path

        # make sure it is absolute
        if not os.path.isabs(path):
            return os.path.abspath(path)
        else:
            return path

    def _ensure_boolean(self, _value):
        if _value.lower() in self._truth:
            return True
        else:
            return False

    def get_value(self, key, value_type=None):
        if not value_type:
            # return str by default
            return self._config.get(self._section_name, key)
        elif value_type == int:
            return self._config.getint(self._section_name, key)
        elif value_type == bool:
            return self._config.getboolean(self._section_name, key)

    def set_value(self, key, value):
        _v = None
        if not isinstance(value, str):
            _v = str(value)
        else:
            _v = value

        if self._section_name not in self._config.sections():
            self._config.add_section(self._section_name)

        self._config[self._section_name][key] = _v
