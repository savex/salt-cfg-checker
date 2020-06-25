import os

from cfg_checker.common import logger_cli


def basic_model_validation_by_path(path):
    logger_cli.debug("\t...validating '{}' as a model".format(path))
    _checks = []
    _is_folder = os.path.isdir(path)
    logger_cli.debug("\t- folder? -> {}".format(_is_folder))
    _checks.append(_is_folder)
    _has_classes = os.path.isdir(os.path.join(path, "classes"))
    logger_cli.debug("\t- has classes? -> {}".format(_has_classes))
    _checks.append(_has_classes)
    _has_cluster = os.path.isdir(os.path.join(path, "classes", "cluster"))
    logger_cli.debug("\t- has classes/cluster? -> {}".format(_has_cluster))
    _checks.append(_has_cluster)
    _has_system = os.path.isdir(os.path.join(path, "classes", "system"))
    logger_cli.debug("\t- has classes/system? -> {}".format(_has_system))
    _checks.append(_has_system)
    _has_nodes = os.path.isdir(os.path.join(path, "nodes"))
    logger_cli.debug("\t- has nodes? -> {}".format(_has_nodes))
    _checks.append(_has_nodes)

    logger_cli.debug("\t-> {}".format(
        all(_checks)
    ))

    return all(_checks)
