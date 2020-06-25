from cfg_checker.common.log import logger, logger_cli

from cfg_checker.common.other import Utils

from cfg_checker.common.settings import config


def nested_set(_d, _keys, _value):
    # # import and deepcopy for safety
    # from copy import deepcopy
    # _d = deepcopy(_dict)
    # process
    for k in _keys[:-1]:
        _d = _d.setdefault(k, {})
    _d[_keys[-1]] = _value


utils = Utils()
logger = logger
logger_cli = logger_cli
config = config
