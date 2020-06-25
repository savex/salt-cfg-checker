import os
import sys
from logging import DEBUG, INFO

from cfg_checker.cli.command import execute_command, helps, parsers
from cfg_checker.common import config, logger, logger_cli
from cfg_checker.helpers.args_utils import MyParser

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.normpath(pkg_dir)


def config_check_entrypoint():
    """
    Main entry point. Uses nested parsers structure
    with a default function to execute the comand

    :return: - no return value
    """
    # Main entrypoint
    parser = MyParser(prog="# Mirantis Cloud configuration checker")

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

    parser.add_argument(
        '--skip-nodes',
        metavar='skip_string', default=None,
        help="String with nodes to skip. Only trailing '*' supported!"
             " Example: 'cmp*,ctl01'"
    )

    parser.add_argument(
        '--skip-nodes-file',
        metavar='skip_nodes_file', default=None,
        help="Filename with nodes to skip. Note: use fqdn node names."
    )

    subparsers = parser.add_subparsers(dest='command')

    # create parsers
    for _command in helps.keys():
        _parser = subparsers.add_parser(
            _command,
            help=helps[_command]
        )
        parsers[_command](_parser)

    # parse arguments
    try:
        args, unknown = parser.parse_known_args()
    except TypeError:
        logger_cli.info("\n# Please, check arguments")
        sys.exit(1)

    if unknown:
        logger_cli.error(
            "# Unexpected arguments: {}".format(
                ", ".join(["'{}'".format(a) for a in unknown])
            )
        )
        sys.exit(1)

    # Pass externally configured values
    config.ssh_uses_sudo = args.sudo

    # Handle options
    if args.debug:
        logger_cli.setLevel(DEBUG)
    else:
        logger_cli.setLevel(INFO)

    # Execute the command
    result = execute_command(args, args.command)
    logger.debug(result)
    sys.exit(result)


if __name__ == '__main__':
    config_check_entrypoint()
