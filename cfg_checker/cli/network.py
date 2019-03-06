from cfg_checker.modules.network.checker import NetworkChecker

if __name__ == '__main__':
    # init connection to salt and collect minion data
    cl = NetworkChecker()

    # collect data on installed packages
    cl.collect_network_info()

    # diff installed and candidates
    # cl.collect_packages()

    # report it
    cl.create_html_report("./pkg_versions.html")
