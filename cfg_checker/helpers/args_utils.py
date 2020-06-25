import argparse
import os
import sys

from cfg_checker.common.exception import ConfigException


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('Error: {0}\n\n'.format(message))
        self.print_help()


def get_skip_args(args):
    if hasattr(args, "skip_nodes"):
        _skip = getattr(args, "skip_nodes")
        if _skip:
            _skip = _skip.split(',')
    else:
        _skip = None
    if hasattr(args, "skip_nodes_file"):
        _skip_file = getattr(args, "skip_nodes_file")
    else:
        _skip_file = None
    return _skip, _skip_file


def get_arg(args, str_arg):
    _attr = getattr(args, str_arg)
    if _attr:
        return _attr
    else:
        _c = args.command if hasattr(args, 'command') else ''
        _t = args.type if hasattr(args, 'type') else ''
        raise ConfigException(
            "Argument '{}' not found executing: mcp-check {} {}".format(
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


def get_network_map_type_and_filename(args):
    if args.html or args.text:
        if args.html and args.text:
            raise ConfigException("Multuple report types not supported")
        if args.html is not None:
            return 'html', args.html
        if args.text is not None:
            return 'text', args.text
    else:
        return 'console', None


def get_package_report_type_and_filename(args):
    if args.html or args.csv:
        if args.html and args.csv:
            raise ConfigException("Multuple report types not supported")
        if args.html is not None:
            return 'html', args.html
        if args.csv is not None:
            return 'csv', args.csv
    else:
        raise ConfigException("Report type and filename not set")
