import argparse
import os
import sys
import traceback
from logging import INFO,  DEBUG

import reporter
from cfg_checker.common.exception import ConfigException
from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.clients import salt

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
    logger_cli.info("Reclass list: to be implemented")

    return


def reclass_diff(args):
    logger_cli.info("Reclass comparer (HTML report: '{}'".format(args.file))
    _filename = get_file_arg(args)

    return


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

    reclass_diff_parser = reclass_subparsers.add_parser(
        'diff',
        help="List models available to compare"
    )

    #parse arguments
    try:
        args = parser.parse_args()
    except TypeError as e:
        logger_cli.info("\nPlease, check arguments")
        return

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
    except ConfigException as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger_cli.error("\nERROR: {}\n\n{}".format(
            e.message,
            "".join(traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback
            ))
        ))
