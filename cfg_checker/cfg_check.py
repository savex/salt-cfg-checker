import argparse
import os
import sys
import traceback

from logging import INFO,  DEBUG

from cfg_checker.common.exception import CheckerException
from cfg_checker.common import config, logger, logger_cli


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


def config_check_entrypoint():
    """
    Main entry point. Uses nested parsers structure 
    with a default function to execute the comand

    :return: - no return value
    """
    # Main entrypoint
    parser = MyParser(prog="# Mirantis Cloud configuration checker")
    
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
    pkg_report_parser.add_argument(
        '--full',
        metavar='packages_html_filename',
        help="HTML report will have all of the packages, not just errors"
    )
    pkg_report_parser.add_argument(
        '--html',
        metavar='packages_html_filename',
        help="HTML filename to save report"
    )
    pkg_report_parser.add_argument(
        '--csv',
        metavar='packages_csv_filename',
        help="CSV filename to save report"
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

    net_report_parser.add_argument(
        '--html',
        metavar='network_html_filename',
        help="HTML filename to save report"
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
    reclass_diff_parser.add_argument(
        '--html',
        metavar='reclass_html_filename',
        help="HTML filename to save report"
    )



    #parse arguments
    try:
        args = parser.parse_args()
    except TypeError as e:
        logger_cli.info("\n# Please, check arguments")
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
        logger_cli.info("\n# Please, type a command listed above")
        return
    elif args.type not in commands[args.command]:
        # check type
        logger_cli.info(
            "\n# Please, select '{}' command type listed above".format(
                args.command
            )
        )
        return
    else:
        # form function name to call
        _method_name = "do_" + args.type
        _target_module = __import__("cfg_checker.modules."+args.command, fromlist=[""])
        _method = getattr(_target_module, _method_name)
    
    # Execute the command
    result = _method(args)

    logger.debug(result)

def cli_main():
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

if __name__ == '__main__':
    cli_main()
