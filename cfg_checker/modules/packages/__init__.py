import checker

from cfg_checker.helpers import args_utils


def do_report(args):
    """Create package versions report, HTML

    :args: - parser arguments
    :return: - no return value
    """
    _type, _filename = args_utils.get_report_type_and_filename(args)

    # init connection to salt and collect minion data
    pChecker = checker.CloudPackageChecker()
    # collect data on installed packages
    pChecker.collect_installed_packages()
    # diff installed and candidates
    pChecker.collect_packages()
    # report it
    pChecker.create_report(_filename, rtype=_type, full=args.full)
