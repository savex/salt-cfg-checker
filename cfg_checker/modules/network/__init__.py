import checker

from cfg_checker.helpers import args_utils
from cfg_checker.common import logger_cli

def do_check(args):
    logger_cli.info("# Network check (CLI output)")
    netChecker = checker.NetworkChecker()
    netChecker.collect_network_info()
    netChecker.print_network_report()

    return


def do_report(args):
    logger_cli.info("# Network check (HTML report: '{}')".format(args.file))
    _filename = args_utils.get_file_arg(args)

    netChecker = checker.NetworkChecker()
    netChecker.collect_network_info()
    netChecker.create_html_report(_filename)

    return
