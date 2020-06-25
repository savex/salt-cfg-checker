from cfg_checker.helpers import args_utils
from cfg_checker.modules.packages.repos import RepoManager

from . import checker

command_help = "Package versions check (Candidate vs Installed)"


def init_parser(_parser):
    # packages subparser
    pkg_subparsers = _parser.add_subparsers(dest='type')

    pkg_report_parser = pkg_subparsers.add_parser(
        'report',
        help="Report package versions to HTML file"
    )
    pkg_report_parser.add_argument(
        '--full',
        action="store_true", default=False,
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
    pkg_report_parser.add_argument(
        '--force-tag',
        metavar='force_tag', default=None,
        help="Tag to do a forced search of release versions in. "
             "If nothing is found, 'mcp_version' tag will be used"
    )
    pkg_report_parser.add_argument(
        '--exclude-keywords',
        metavar='exclude_repos_keywords', default="nightly extra",
        help="Keywords to exclude repos from searching "
             "release versions. Space delimited: 'nightly extra'"
    )
    pkg_repos = pkg_subparsers.add_parser(
        'versions',
        help="Parse versions at given URL and create local map"
    )
    pkg_repos.add_argument(
        '--list-tags',
        action="store_true", default=False,
        help="Just list tags available in mirror"
    )
    pkg_repos.add_argument(
        '--url',
        metavar='repo_url', default="http://mirror.mirantis.com",
        help="URL for repos, default: http://mirror.mirantis.com"
    )
    pkg_repos.add_argument(
        '--tag',
        metavar='repo_tag', default=None,
        help="Repository tag to process packages from. Default: "
        "All url's root folder tags"
    )
    pkg_repos.add_argument(
        '--build-repos',
        action="store_true", default=False,
        help="Conduct build stage before working with tags"
    )
    pkg_repos.add_argument(
        '--gen-desc',
        action="store_true", default=False,
        help="Save pkg descriptions while parsing"
    )
    pkg_repos.add_argument(
        '--gen-apps',
        action="store_true", default=False,
        help="Save pkg descriptions while parsing"
    )
    pkg_show = pkg_subparsers.add_parser(
        'show',
        help="Show package history from the map"
    )
    pkg_show.add_argument(
        'args',
        nargs='+',
        help="Package names separated by space"
    )
    pkg_app = pkg_subparsers.add_parser(
        'show-app',
        help="Show packages for single app"
    )
    pkg_app.add_argument(
        'args',
        nargs='+',
        help="List of app's packages (or 'source' in package description)"
    )

    return _parser


def do_report(args):
    """Create package versions report, HTML

    :args: - parser arguments
    :return: - no return value
    """
    _type, _filename = args_utils.get_package_report_type_and_filename(args)

    if ' ' in args.exclude_keywords:
        _kw = args.exclude_keywords.split(' ')
    else:
        _kw = [args.exclude_keywords]

    # init connection to salt and collect minion data
    _skip, _skip_file = args_utils.get_skip_args(args)
    pChecker = checker.CloudPackageChecker(
        force_tag=args.force_tag,
        exclude_keywords=_kw,
        skip_list=_skip,
        skip_list_file=_skip_file
    )
    # collect data on installed packages
    pChecker.collect_installed_packages()
    # diff installed and candidates
    pChecker.collect_packages()
    # report it
    pChecker.create_report(_filename, rtype=_type, full=args.full)


def do_versions(args):
    """Builds tagged repo structure and parses Packages.gz files

    :args: - parser arguments
    :return: - no return value
    """
    # Get the list of tags for the url
    r = RepoManager()
    if args.list_tags:
        r.action_for_tag(args.url, args.tag, action="list")
        return
    if args.build_repos:
        # if tag is supplied, use it
        if args.tag:
            r.action_for_tag(args.url, args.tag, action="build")
        else:
            r.build_repos(args.url)

    if args.tag:
        # Process only this tag
        r.action_for_tag(
            args.url,
            args.tag,
            action="fetch",
            descriptions=args.gen_desc,
            apps=args.gen_apps
        )
    else:
        # All of them
        r.parse_repos()


def do_show(args):
    """Shows package (or multiple) history across parsed tags
    """
    # Init manager
    r = RepoManager()
    # show packages
    for p in args.args:
        r.show_package(p)


def do_show_app(args):
    """Shows packages for app
    """
    # Init manager
    r = RepoManager()
    # show packages
    for a in args.args:
        r.show_app(a)
