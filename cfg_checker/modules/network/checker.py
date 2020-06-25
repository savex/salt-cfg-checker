from cfg_checker.common import logger_cli
from cfg_checker.modules.network.mapper import NetworkMapper
from cfg_checker.modules.network.network_errors import NetworkErrors
from cfg_checker.reports import reporter


class NetworkChecker(object):
    def __init__(
        self,
        skip_list=None,
        skip_list_file=None
    ):
        logger_cli.debug("... init error logs folder")
        self.errors = NetworkErrors()
        self.mapper = NetworkMapper(
            self.errors,
            skip_list=skip_list,
            skip_list_file=skip_list_file
        )

    def check_networks(self, map=True):
        self.mapper.map_network(self.mapper.RECLASS)
        self.mapper.map_network(self.mapper.RUNTIME)

        self.mapper.create_map()
        if map:
            self.mapper.print_map()

    def print_summary(self):
        logger_cli.info(self.errors.get_summary(print_zeros=False))

    def print_error_details(self):
        # Detailed errors
        logger_cli.info(
            "\n{}\n".format(
                self.errors.get_errors()
            )
        )

    def create_html_report(self, filename):
        """
        Create static html showing network schema-like report

        :return: none
        """
        logger_cli.info("### Generating report to '{}'".format(filename))
        _report = reporter.ReportToFile(
            reporter.HTMLNetworkReport(),
            filename
        )
        _report({
            "domain": self.mapper.domain,
            "nodes": self.mapper.nodes,
            "map": self.mapper.map,
            "mcp_release": self.mapper.cluster['mcp_release'],
            "openstack_release": self.mapper.cluster['openstack_release']

        })
        logger_cli.info("-> Done")
