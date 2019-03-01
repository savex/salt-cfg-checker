import os

from cfg_checker.common.exception import ConfigException


def get_file_arg(args):
    if args.file:
        return args.file
    else:
        raise ConfigException("No report filename supplied")


def get_path_arg(path):
    if os.path.exists(path):
        return path
    else:
        raise ConfigException("'{}' not exists".format(path))
