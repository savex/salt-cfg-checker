import os

from cfg_checker.common.exception import ConfigException


def get_file_arg(args):
    if args.file:
        return args.file
    else:
        raise ConfigException("No report filename supplied")


def get_path_arg(path):
    if os.path.exists(path):
        return path
    else:
        raise ConfigException("'{}' not exists".format(path))


def get_report_type_and_filename(args):
    if hasattr(args, 'html') or hasattr(args, 'csv'):
        if args.html and args.csv:
            raise ConfigException("Multuple report types not supported")
        if args.html is not None:
            return 'html', args.html
        if args.csv is not None:
            return 'csv', args.csv
    else:
        raise ConfigException("Report type and filename not set")
