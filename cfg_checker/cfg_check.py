import argparse
import os
import sys

import reporter
from cfg_checker.common import utils, const
from cfg_checker.common import config, logger, logger_cli, pkg_dir
from cfg_checker.clients import salt

from cfg_checker.pkg_check import CloudPackageChecker

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.normpath(pkg_dir)


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

def pkg_check(args):
    # create package versions report
    if args.file:
        _filename = args.file
    else:
        logger_cli.error("ERROR: no report filename supplied")
        return
    # init connection to salt and collect minion data
    pChecker = CloudPackageChecker()
    # collect data on installed packages
    pChecker.collect_installed_packages()
    # diff installed and candidates
    # pChecker.collect_packages()
    # report it
    pChecker.create_html_report(_filename)


def net_check(args):
    print("This is net check routine")

    return


def net_report(args):
    print("This is net check routine")

    return


def config_check_entrypoint():
    # Main entrypointр
    parser = MyParser(prog="Cloud configuration checker")
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
    pkg_report_parser.add_argument(
        '-f',
        '--file',
        help="HTML filename to save report"
    )
    pkg_report_parser.set_defaults(func=pkg_check)

    # networking
    net_parser = subparsers.add_parser(
        'network',
        help="Network infrastructure checks"
    )
    net_subparsers = net_parser.add_subparsers(dest='type')

    net_check_parser = net_subparsers.add_parser(
        'check',
        help="Do network check and print the result"
    )
    net_check_parser.set_defaults(func=net_check)

    net_report_parser = net_subparsers.add_parser(
        'report',
        help="Generate network check report"
    )
    net_report_parser.add_argument(
        '-f',
        '--file',
        help="HTML filename to save report"
    )
    net_report_parser.set_defaults(func=net_report)
    
    #parse arguments
    args = parser.parse_args()

    # Execute the command
    result = args.func(args)

    logger.debug(result)
    return

if __name__ == '__main__':
    try:
        config_check_entrypoint()
    except Exception as e:
        logger_cli.error("ERROR: {}".format(e.message))
