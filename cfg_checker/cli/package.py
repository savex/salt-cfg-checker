from cfg_checker.packages.checker import CloudPackageChecker


if __name__ == '__main__':
    # init connection to salt and collect minion data
    cl = CloudPackageChecker()

    # collect data on installed packages
    cl.collect_installed_packages()

    # diff installed and candidates
    # cl.collect_packages()

    # report it
    cl.create_html_report("./pkg_versions.html")
