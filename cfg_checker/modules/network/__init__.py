from cfg_checker.common import logger_cli
from cfg_checker.helpers import args_utils
from cfg_checker.modules.network import checker, mapper, pinger


command_help = "Network infrastructure checks and reports"


def init_parser(_parser):
    # network subparser
    net_subparsers = _parser.add_subparsers(dest='type')

    net_check_parser = net_subparsers.add_parser(
        'check',
        help="Do network check and print the result"
    )

    net_check_parser.add_argument(
        '--detailed',
        action="store_true", default=False,
        help="Print error details after summary"
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

    net_ping_parser = net_subparsers.add_parser(
        'ping',
        help="Ping all nodes with each other using network CIDR"
    )

    net_ping_parser.add_argument(
        '--cidr',
        metavar='network_ping_cidr',
        help="Subnet CIDR to ping nodes in"
    )
    net_ping_parser.add_argument(
        '--mtu',
        metavar='network_ping_mtu',
        help="MTU size to use. Ping will be done for MTU - 20 - 8"
    )
    net_ping_parser.add_argument(
        '--detailed',
        action="store_true", default=False,
        help="Print detailed report at the end"
    )

    net_subparsers.add_parser(
        'map',
        help="Print network map"
    )

    net_subparsers.add_parser(
        'list',
        help="List networks in reclass"
    )

    return _parser


def do_check(args):
    # Net Checks
    # should not print map, etc...
    # Just bare summary and errors
    logger_cli.info("# Network check to console")
    _skip, _skip_file = args_utils.get_skip_args(args)
    netChecker = checker.NetworkChecker(
        skip_list=_skip,
        skip_list_file=_skip_file
    )
    netChecker.check_networks()

    # save what was collected
    netChecker.errors.save_iteration_data()

    # print a report
    netChecker.print_summary()

    # if set, print details
    if args.detailed:
        netChecker.print_error_details()


def do_report(args):
    # Network Report
    # should generate Static HTML page
    # with node/network map and values

    logger_cli.info("# Network report (check, node map")

    _filename = args_utils.get_arg(args, 'html')
    _skip, _skip_file = args_utils.get_skip_args(args)
    netChecker = checker.NetworkChecker(
        skip_list=_skip,
        skip_list_file=_skip_file
    )
    netChecker.check_networks(map=False)

    # save what was collected
    netChecker.errors.save_iteration_data()
    netChecker.create_html_report(_filename)

    return


def do_map(args):
    # Network Map
    # Should generate network map to console or HTML
    logger_cli.info("# Network report")
    _skip, _skip_file = args_utils.get_skip_args(args)
    networkMap = mapper.NetworkMapper(
        skip_list=_skip,
        skip_list_file=_skip_file
    )
    networkMap.prepare_all_maps()
    networkMap.create_map()
    networkMap.print_map()

    return


def do_list(args):
    # Network List
    # Should generate network map to console or HTML
    _skip, _skip_file = args_utils.get_skip_args(args)
    _map = mapper.NetworkMapper(
        skip_list=_skip,
        skip_list_file=_skip_file
    )
    reclass = _map.map_network(_map.RECLASS)
    runtime = _map.map_network(_map.RUNTIME)

    _s = [str(_n) for _n in reclass.keys()]
    logger_cli.info("\n# Reclass networks list")
    logger_cli.info("\n".join(_s))
    _s = [str(_n) for _n in runtime.keys()]
    logger_cli.info("\n# Runtime networks list")
    logger_cli.info("\n".join(_s))

    return


def do_ping(args):
    # Network pinger
    # Checks if selected nodes are pingable
    # with a desireble parameters: MTU, Frame, etc
    if not args.cidr:
        logger_cli.error("\n# Use mcp-check network list to get list of CIDRs")
    _cidr = args_utils.get_arg(args, "cidr")
    _skip, _skip_file = args_utils.get_skip_args(args)
    _pinger = pinger.NetworkPinger(
        mtu=args.mtu,
        detailed=args.detailed,
        skip_list=_skip,
        skip_list_file=_skip_file
    )

    _ret = _pinger.ping_nodes(_cidr)

    if _ret < 0:
        # no need to save the iterations and summary
        return
    else:
        # save what was collected
        _pinger.errors.save_iteration_data()

        # print a report
        _pinger.print_summary()

        # if set, print details
        if args.detailed:
            _pinger.print_details()

        return


def do_trace(args):
    # Network packet tracer
    # Check if packet is delivered to proper network host
    logger_cli.info("# Packet Tracer not yet implemented")

    # TODO: Packet tracer

    return
