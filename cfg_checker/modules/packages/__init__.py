import checker

from cfg_checker.helpers import args_utils


def do_report(args):
    """Create package versions report

    :args: - parser arguments
    :return: - no return value
    """
    _filename = args_utils.get_file_arg(args)

    # init connection to salt and collect minion data
    pChecker = checker.CloudPackageChecker()
    # collect data on installed packages
    pChecker.collect_installed_packages()
    # diff installed and candidates
    # pChecker.collect_packages()
    # report it
    pChecker.create_html_report(_filename)
