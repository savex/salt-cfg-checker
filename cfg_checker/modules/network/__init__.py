import checker

from cfg_checker.helpers import args_utils
from cfg_checker.common import logger_cli

def _prepare_check():
    _checker_class = checker.NetworkChecker()
    _checker_class.collect_reclass_networks()
    _checker_class.collect_network_info()
    return _checker_class

def do_check(args):
    logger_cli.info("# Network check to console")
    netChecker = _prepare_check()
    netChecker.print_network_report()

    return


def do_report(args):
    logger_cli.info("# Network report")

    _filename = args_utils.get_arg(args, 'html')
    
    netChecker = _prepare_check()
    netChecker.create_html_report(_filename)

    return
