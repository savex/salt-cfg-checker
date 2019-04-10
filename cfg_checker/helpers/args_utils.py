import os

from cfg_checker.common.exception import ConfigException


def get_arg(args, str_arg):
    _attr = getattr(args, str_arg)
    if _attr:
        return _attr
    else:
        _c = args.command if hasattr(args, 'command') else ''
        _t = args.type if hasattr(args, 'type') else ''
        raise ConfigException(
            "Argument '{}' not found executing: mcp_check {} {}".format(
                str_arg,
                _c,
                _t
            )
        )


def get_path_arg(path):
    if os.path.exists(path):
        return path
    else:
        raise ConfigException("'{}' not exists".format(path))


def get_report_type_and_filename(args):
    if args.html or args.csv:
        if args.html and args.csv:
            raise ConfigException("Multuple report types not supported")
        if args.html is not None:
            return 'html', args.html
        if args.csv is not None:
            return 'csv', args.csv
    else:
        raise ConfigException("Report type and filename not set")
