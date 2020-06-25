import pkgutil
import sys
import traceback

from cfg_checker.common import config, logger, logger_cli
from cfg_checker.common.exception import CheckerException
from cfg_checker.helpers.args_utils import MyParser

main_pkg_name = __name__.split('.')[0]
mods_package_name = "modules"
mods_import_path = main_pkg_name + '.' + mods_package_name
mods_prefix = mods_import_path + '.'

commands = {}
parsers = {}
helps = {}
# Pure dynamic magic, loading all 'do_*' methods from available modules
_m = __import__(mods_import_path, fromlist=[main_pkg_name])
for _imp, modName, isMod in pkgutil.iter_modules(_m.__path__, mods_prefix):
    # iterate all packages, add to dict
    if isMod:
        # load module
        _p = _imp.find_module(modName).load_module(modName)
        # create a shortname
        mod_name = modName.split('.')[-1]
        # A package! Create it and add commands
        commands[mod_name] = \
            [_n[3:] for _n in dir(_p) if _n.startswith("do_")]
        parsers[mod_name] = getattr(_p, 'init_parser')
        helps[mod_name] = getattr(_p, 'command_help')


def execute_command(args, command):
    # Validate the commands
    # check commands
    if not hasattr(args, 'type') or not args.type:
        logger_cli.info("\n# Please, type a command listed above")
        return 1
    _type = args.type.replace("-", "_") if "-" in args.type else args.type
    if command not in commands:
        logger_cli.info("\n# Please, type a command listed above")
        return 1
    elif _type not in commands[command]:
        # check type
        logger_cli.info(
            "\n# Please, select '{}' command type listed above".format(
                command
            )
        )
        return 1
    else:
        # form function name to call
        _method_name = "do_" + _type
        _target_module = __import__(
            mods_prefix + command,
            fromlist=[""]
        )
        _method = getattr(_target_module, _method_name)

    # Execute the command
    try:
        _method(args)
        return 0
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
        return 1


def cli_command(_title, _name):
    my_parser = MyParser(_title)
    parsers[_name](my_parser)

    # parse arguments
    try:
        args, unknown = my_parser.parse_known_args()
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

    # force use of sudo
    config.ssh_uses_sudo = True

    # Execute the command
    result = execute_command(args, _name)
    logger.debug(result)
    sys.exit(result)
