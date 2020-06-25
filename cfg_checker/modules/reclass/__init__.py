import os

from cfg_checker.common import logger_cli
from cfg_checker.helpers import args_utils
from cfg_checker.reports import reporter

from . import comparer

from . import validator

command_help = "Reclass related checks and reports"


def init_parser(_parser):
    # reclass subparsers
    reclass_subparsers = _parser.add_subparsers(dest='type')
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

    return _parser


def do_list(args):
    logger_cli.info("# Reclass list")
    _arg_path = args_utils.get_arg(args, 'models_path')
    logger_cli.info("-> Current path is: {}".format(_arg_path))
    _path = args_utils.get_path_arg(_arg_path)

    logger_cli.info("# ...models path is '{}'".format(_path))

    models = {}
    for _folder in os.listdir(args.models_path):
        # validate item as a model
        _model_path = os.path.join(
            args.models_path,
            _folder
        )
        _validated = validator.basic_model_validation_by_path(_model_path)

        if not _validated:
            logger_cli.info("-> '{}' not a valid model".format(_folder))
            continue
        else:
            models[_folder] = _model_path

        logger_cli.info("-> '{}' at '{}'".format(_folder, _model_path))

        # TODO: collect info about the model

    return


def do_diff(args):
    logger_cli.info("# Reclass comparer (HTML report)")
    _filename = args_utils.get_arg(args, 'html')
    # checking folder params
    _model1 = args_utils.get_path_arg(args.model1)
    _model2 = args_utils.get_path_arg(args.model2)

    # Do actual compare using hardcoded model names
    mComparer = comparer.ModelComparer()

    mComparer.model_name_1 = os.path.split(_model1)[1]
    mComparer.model_path_1 = _model1
    mComparer.model_name_2 = os.path.split(_model2)[1]
    mComparer.model_path_2 = _model2

    mComparer.load_model_tree(
        mComparer.model_name_1,
        mComparer.model_path_1
    )
    mComparer.load_model_tree(
        mComparer.model_name_2,
        mComparer.model_path_2
    )

    diffs = mComparer.generate_model_report_tree()

    report = reporter.ReportToFile(
        reporter.HTMLModelCompare(),
        _filename
    )
    logger_cli.info("# Generating report to {}".format(_filename))
    report({
        "nodes": {},
        "diffs": diffs
    })
