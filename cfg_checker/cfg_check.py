import argparse
import os
import reclass
import sys
import traceback

from logging import INFO,  DEBUG

import reporter

from cfg_checker.common.exception import CheckerException, ConfigException
from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.clients import salt

import cfg_checker.reclass_cmp as reclass_cmp
from cfg_checker.pkg_check import CloudPackageChecker
from cfg_checker.network_checks import NetworkChecker

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.normpath(pkg_dir)

commands = {
    'packages': ['report'],
    'network': ['check', 'report'],
    'reclass': ['list', 'diff']
}

class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('Error: {0}\n\n'.format(message))
        self.print_help()


def help_message():
    print"""
    Please, use following examples to generate info reports:\n
         cfg_checker packages report\n
         cfg_checker network check\n
         cfg_checker network report\n
    """
    return


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


def validate_model(path):
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


def packages_report(args):
    """Create package versions report

    :args: - parser arguments
    :return: - no return value
    """
    _filename = get_file_arg(args)

    # init connection to salt and collect minion data
    pChecker = CloudPackageChecker()
    # collect data on installed packages
    pChecker.collect_installed_packages()
    # diff installed and candidates
    # pChecker.collect_packages()
    # report it
    pChecker.create_html_report(_filename)


def network_check(args):
    logger_cli.info("# Network check (CLI output)")
    netChecker = NetworkChecker()
    netChecker.collect_network_info()
    netChecker.print_network_report()

    return


def network_report(args):
    logger_cli.info("# Network check (HTML report: '{}')".format(args.file))
    _filename = get_file_arg(args)

    netChecker = NetworkChecker()
    netChecker.collect_network_info()
    netChecker.create_html_report(_filename)

    return


def reclass_list(args):
    logger_cli.info("# Reclass list")
    _path = get_path_arg(args.models_path)
    
    logger_cli.info("# ...models path is '{}'".format(args.models_path))
    
    models = {}
    for _folder in os.listdir(args.models_path):
        # validate item as a model
        _model_path = os.path.join(
            args.models_path,
            _folder
        )
        _validated = validate_model(_model_path)
        
        if not _validated:
            logger_cli.info("-> '{}' not a valid model".format(_folder))
            continue
        else:
            models[_folder] = _model_path
        
        logger_cli.info("-> '{}' at '{}'".format(_folder, _model_path))
        
        # TODO: collect info about the model

    return


def reclass_diff(args):
    logger_cli.info("Reclass comparer (HTML report: '{}'".format(args.file))
    _filename = get_file_arg(args)

    # checking folder params
    _model1 = get_path_arg(args.model1)
    _model2 = get_path_arg(args.model2)
    
    # Do actual compare using hardcoded model names
    mComparer = reclass_cmp.ModelComparer()

    mComparer.model_name_1 = os.path.split(_model1)[1]
    mComparer.model_path_1 = _model1
    mComparer.model_name_2 = os.path.split(_model2)[1]
    mComparer.model_path_2 = _model2
    
    mComparer.load_model_tree(
        mComparer.model_name_1,
        mComparer.model_path_1
    )
    mComparer.load_model_tree(
        mComparer.model_name_2,
        mComparer.model_path_2
    )

    diffs = mComparer.generate_model_report_tree()

    report = reporter.ReportToFile(
        reporter.HTMLModelCompare(),
        _filename
    )
    logger_cli.info("# Generating report to {}".format(_filename))
    report({
        "nodes": {},
        "diffs": diffs
    })


def config_check_entrypoint():
    """
    Main entry point. Uses nested parsers structure 
    with a default function to execute the comand

    :return: - no return value
    """
    # Main entrypointр
    parser = MyParser(prog="Cloud configuration checker")
    
    # Parsers (each parser can have own arguments)
    # - subparsers (command)
    #   |- pkg_parser
    #   |  - pkg_subparsers (type)
    #   |    - pkg_report_parser (default func - pkg_check)
    #   |- net_parser
    #   |  - net_subparsers (type)
    #   |    - net_check_parser (default func - net_check)
    #   |    - net_report_parser (default func - net_report)
    #    - reclass_parser
    #      - reclass_list (default func - reclass_list)
    #      - reclass_compare (default func - reclass_diff)

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true", default=False,
        help="Set CLI logging level to DEBUG"
    )
    parser.add_argument(
        '-f',
        '--file',
        help="HTML filename to save report"
    )
    parser.add_argument(
        '-s',
        '--sudo',
        action='store_true', default=True,
        help="Use sudo for getting salt creds"
    )
    subparsers = parser.add_subparsers(dest='command')
    # packages
    pkg_parser = subparsers.add_parser(
        'packages',
        help="Package versions check (Candidate vs Installed)"
    )
    pkg_subparsers = pkg_parser.add_subparsers(dest='type')

    pkg_report_parser = pkg_subparsers.add_parser(
        'report',
        help="Report package versions to HTML file"
    )

    # networking
    net_parser = subparsers.add_parser(
        'network',
        help="Network infrastructure checks and reports"
    )
    net_subparsers = net_parser.add_subparsers(dest='type')

    net_check_parser = net_subparsers.add_parser(
        'check',
        help="Do network check and print the result"
    )

    net_report_parser = net_subparsers.add_parser(
        'report',
        help="Generate network check report"
    )
    
    # reclass
    reclass_parser = subparsers.add_parser(
        'reclass',
        help="Reclass related checks and reports"
    )
    reclass_subparsers = reclass_parser.add_subparsers(dest='type')
    reclass_list_parser = reclass_subparsers.add_parser(
        'list',
        help="List models available to compare"
    )
    reclass_list_parser.add_argument(
        "-p",
        "--models-path",
        default="/srv/salt/",
        help="Global path to search models in"
    )

    reclass_diff_parser = reclass_subparsers.add_parser(
        'diff',
        help="List models available to compare"
    )
    reclass_diff_parser.add_argument(
        "--model1",
        required=True,
        help="Model A <path>. Model name is the folder name"
    )
    reclass_diff_parser.add_argument(
        "--model2",
        required=True,
        help="Model B <path>. Model name is the folder name"
    )


    #parse arguments
    try:
        args = parser.parse_args()
    except TypeError as e:
        logger_cli.info("\nPlease, check arguments")
        return

    # Pass externally configured values
    config.ssh_uses_sudo = args.sudo
    
    # Handle options
    if args.debug:
        logger_cli.setLevel(DEBUG)
    else:
        logger_cli.setLevel(INFO)

    # Validate the commands
    # check command
    if args.command not in commands:
        logger_cli.info("\nPlease, type a command listed above")
        return
    elif args.type not in commands[args.command]:
        # check type
        logger_cli.info(
            "\nPlease, select '{}' command type listed above".format(
                args.command
            )
        )
        return
    else:
        # form function name to call
        _method_name = args.command + "_" + args.type
        _this_module = sys.modules[__name__]
        _method = getattr(_this_module, _method_name)
    
    # Execute the command
    result = _method(args)

    logger.debug(result)

if __name__ == '__main__':
    try:
        config_check_entrypoint()
    except CheckerException as e:
        logger_cli.error("\nERROR: {}".format(
            e.message
        ))

        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger_cli.debug("\n{}".format(
            "".join(traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback
            ))
        ))
