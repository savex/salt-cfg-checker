import json

from cfg_checker.common import const, logger_cli
from cfg_checker.common.exception import ConfigException
from cfg_checker.common.other import merge_dict
from cfg_checker.helpers.console_utils import Progress
from cfg_checker.modules.packages.repos import RepoManager
from cfg_checker.nodes import salt_master
from cfg_checker.reports import reporter

from .versions import DebianVersion, PkgVersions, VersionCmpResult


class CloudPackageChecker(object):
    def __init__(
        self,
        force_tag=None,
        exclude_keywords=[],
        skip_list=None,
        skip_list_file=None
    ):
        # Init salt master info
        if not salt_master.nodes:
            salt_master.nodes = salt_master.get_nodes(
                skip_list=skip_list,
                skip_list_file=skip_list_file
            )

        # check that this env tag is present in Manager
        self.rm = RepoManager()
        _tags = self.rm.get_available_tags(tag=salt_master.mcp_release)
        if not _tags:
            logger_cli.warning(
                "\n# hWARNING: '{0}' is not listed in repo index. "
                "Consider running:\n\t{1}\nto add info on this tag's "
                "release package versions".format(
                    salt_master.mcp_release,
                    "mcp-checker packages versions --tag {0}"
                )
            )

        self.force_tag = force_tag
        self.exclude_keywords = exclude_keywords

    @staticmethod
    def presort_packages(all_packages, full=None):
        logger_cli.info("-> Presorting packages")
        # labels
        _data = {}
        _data = {
            "cs": {
                "ok": const.VERSION_OK,
                "up": const.VERSION_UP,
                "down": const.VERSION_DOWN,
                "warn": const.VERSION_WARN,
                "err": const.VERSION_ERR
            },
            "ca": {
                "na": const.ACT_NA,
                "up": const.ACT_UPGRADE,
                "need_up": const.ACT_NEED_UP,
                "need_down": const.ACT_NEED_DOWN,
                "repo": const.ACT_REPO
            }
        }
        _data['status_err'] = const.VERSION_ERR
        _data['status_warn'] = const.VERSION_WARN
        _data['status_down'] = const.VERSION_DOWN
        _data['status_skip'] = const.VERSION_NA

        # Presort packages
        _data['critical'] = {}
        _data['system'] = {}
        _data['other'] = {}
        _data['unlisted'] = {}

        _l = len(all_packages)
        _progress = Progress(_l)
        _progress_index = 0
        # counters
        _ec = _es = _eo = _eu = 0
        _wc = _ws = _wo = _wu = 0
        _dc = _ds = _do = _du = 0
        while _progress_index < _l:
            # progress bar
            _progress_index += 1
            _progress.write_progress(_progress_index)
            # sort packages
            _pn, _val = all_packages.popitem()
            _c = _val['desc']['section']
            _rkeys = _val['results'].keys()

            if not full:
                # Check if this packet has errors
                # if all is ok -> just skip it
                _max_status = max(_val['results'].keys())
                if _max_status <= const.VERSION_OK:
                    _max_action = max(_val['results'][_max_status].keys())
                    if _max_action == const.ACT_NA:
                        # this package does not have any comments
                        # ...just skip it from report
                        continue

            _differ = len(set(_val['results'].keys())) > 1
            if _differ:
                # in case package has different status across nodes
                # Warning becomes Error.
                if const.VERSION_WARN in _val['results']:
                    if const.VERSION_ERR in _val['results']:
                        # add warns to err
                        # should never happen, though
                        merge_dict(
                            _val['results'].pop(const.VERSION_WARN),
                            _val['results'][const.VERSION_ERR]
                        )
                    else:
                        _val['results'][const.VERSION_ERR] = \
                            _val['results'].pop(const.VERSION_WARN)
            else:
                # in case package has same status on all nodes
                # Error becomes Warning
                if const.VERSION_ERR in _val['results']:
                    if const.VERSION_WARN in _val['results']:
                        # add warns to err
                        # should never happen, though
                        merge_dict(
                            _val['results'].pop(const.VERSION_ERR),
                            _val['results'][const.VERSION_WARN]
                        )
                    else:
                        _val['results'][const.VERSION_WARN] = \
                            _val['results'].pop(const.VERSION_ERR)

            if len(_c) > 0 and _val['is_mirantis'] is None:
                # not listed package in version lib
                _data['unlisted'].update({
                    _pn: _val
                })
                _eu += sum(x == const.VERSION_ERR for x in _rkeys)
                _wu += sum(x == const.VERSION_WARN for x in _rkeys)
                _du += sum(x == const.VERSION_DOWN for x in _rkeys)
            # mirantis/critical
            # elif len(_c) > 0 and _c != 'System':
            elif _val['is_mirantis']:
                # not blank and not system
                _data['critical'].update({
                    _pn: _val
                })
                _ec += sum(x == const.VERSION_ERR for x in _rkeys)
                _wc += sum(x == const.VERSION_WARN for x in _rkeys)
                _dc += sum(x == const.VERSION_DOWN for x in _rkeys)
            # system
            elif _c == 'System':
                _data['system'].update({
                    _pn: _val
                })
                _es += sum(x == const.VERSION_ERR for x in _rkeys)
                _ws += sum(x == const.VERSION_WARN for x in _rkeys)
                _ds += sum(x == const.VERSION_DOWN for x in _rkeys)
            # rest
            else:
                _data['other'].update({
                    _pn: _val
                })
                _eo += sum(x == const.VERSION_ERR for x in _rkeys)
                _wo += sum(x == const.VERSION_WARN for x in _rkeys)
                _do += sum(x == const.VERSION_DOWN for x in _rkeys)

        _progress.end()

        _data['errors'] = {
            'mirantis': _ec,
            'system': _es,
            'other': _eo,
            'unlisted': _eu
        }
        _data['warnings'] = {
            'mirantis': _wc,
            'system': _ws,
            'other': _wo,
            'unlisted': _wu
        }
        _data['downgrades'] = {
            'mirantis': _dc,
            'system': _ds,
            'other': _do,
            'unlisted': _du
        }

        return _data

    def collect_installed_packages(self):
        """
        Collect installed packages on each node
        sets 'installed' dict property in the class

        :return: none
        """
        logger_cli.info("# Collecting installed packages")
        salt_master.prepare_script_on_active_nodes("pkg_versions.py")
        _result = salt_master.execute_script_on_active_nodes("pkg_versions.py")

        for key in salt_master.nodes.keys():
            # due to much data to be passed from salt, it is happening in order
            if key in _result and _result[key]:
                _text = _result[key]
                try:
                    _dict = json.loads(_text[_text.find('{'):])
                except ValueError:
                    logger_cli.info("... no JSON for '{}'".format(
                        key
                    ))
                    logger_cli.debug(
                        "ERROR:\n{}\n".format(_text[:_text.find('{')])
                    )
                    _dict = {}

                salt_master.nodes[key]['packages'] = _dict
            else:
                salt_master.nodes[key]['packages'] = {}
            logger_cli.debug("... {} has {} packages installed".format(
                key,
                len(salt_master.nodes[key]['packages'].keys())
            ))
        logger_cli.info("-> Done")

    def collect_packages(self):
        """
        Check package versions in repos vs installed

        :return: no return values, all date put to dict in place
        """
        # Preload OpenStack release versions
        _desc = PkgVersions()
        logger_cli.info(
            "# Cross-comparing: Installed vs Candidates vs Release"
        )
        # shortcuts for this cloud values
        _os = salt_master.openstack_release
        _mcp = salt_master.mcp_release
        _t = [self.force_tag] if self.force_tag else []
        _t.append(_mcp)

        logger_cli.info("# Tag search list: {}".format(", ".join(_t)))
        logger_cli.info("# Openstack version: {}".format(_os))
        logger_cli.info(
            "# Release versions repos keyword exclude list: {}".format(
                ", ".join(self.exclude_keywords)
            )
        )

        # Progress class
        _progress = Progress(len(salt_master.nodes.keys()))
        _progress_index = 0
        _total_processed = 0
        # Collect packages from all of the nodes in flat dict
        _all_packages = {}
        for node_name, node_value in salt_master.nodes.items():
            _uniq_len = len(_all_packages.keys())
            _progress_index += 1
            # progress updates shown before next node only
            # it is costly operation to do it for each of the 150k packages
            _progress.write_progress(
                _progress_index,
                note="/ {} uniq out of {} packages found".format(
                    _uniq_len,
                    _total_processed
                )
            )
            for _name, _value in node_value['packages'].items():
                _total_processed += 1
                # Parse versions from nodes
                _ver_ins = DebianVersion(_value['installed'])
                _ver_can = DebianVersion(_value['candidate'])

                # Process package description and release version
                # at a first sight
                if _name not in _all_packages:
                    # get node attributes
                    _linux = salt_master.nodes[node_name]['linux_codename']
                    _arch = salt_master.nodes[node_name]['linux_arch']
                    # get versions for tag, Openstack release and repo headers
                    # excluding 'nightly' repos by default
                    _r = {}
                    # if there is a forced tag = use it
                    if self.force_tag:
                        _r = self.rm.get_filtered_versions(
                            _name,
                            tag=self.force_tag,
                            include=[_os, _linux, _arch],
                            exclude=self.exclude_keywords
                        )
                        # if nothing found, look everywhere
                        # but with no word 'openstack'
                        if not _r:
                            _r = self.rm.get_filtered_versions(
                                _name,
                                tag=self.force_tag,
                                include=[_linux, _arch],
                                exclude=self.exclude_keywords + ['openstack']
                            )
                    # if nothing is found at this point,
                    # repeat search using normal tags
                    if not _r:
                        _r = self.rm.get_filtered_versions(
                            _name,
                            tag=_mcp,
                            include=[_os, _linux, _arch],
                            exclude=self.exclude_keywords
                        )
                    # Once again, if nothing found, look everywhere
                    if not _r:
                        _r = self.rm.get_filtered_versions(
                            _name,
                            tag=_mcp,
                            include=[_linux, _arch],
                            exclude=self.exclude_keywords + ['openstack']
                        )
                    # repack versions in flat format
                    _vs = {}
                    _sections = {}
                    _apps = {}
                    for s, apps in _r.items():
                        for a, versions in apps.items():
                            for v, repos in versions.items():
                                for repo in repos:
                                    if v not in _vs:
                                        _vs[v] = []
                                    _vs[v].append(repo)
                                    if v not in _sections:
                                        _sections[v] = []
                                    _sections[v].append(s)
                                    if v not in _apps:
                                        _apps[v] = []
                                    _apps[v].append(a)
                    # search for the newest version among filtered
                    _r_desc = []
                    _vs_keys = iter(_vs.keys())
                    # get next version, if any
                    try:
                        _newest = DebianVersion(next(_vs_keys))
                    except StopIteration:
                        _newest = DebianVersion('')
                    # iterate others, if any
                    for v in _vs_keys:
                        _this = DebianVersion(v)
                        if _this > _newest:
                            _newest = _this
                    _release = _newest
                    # Get best description for the package
                    if _release.version != 'n/a':
                        _r_desc = _vs[_release.version]
                    # preload special description
                    if _desc[_name]:
                        _pkg_desc = _desc[_name]
                    else:
                        _pkg_desc = _desc.dummy_desc
                    # Save repos list and desc for this version
                    # Check if we can provide better from the package
                    if _release.version != 'n/a':
                        if not _pkg_desc['section']:
                            _pkg_desc['section'] = \
                                "/".join(_sections[_release.version])
                        if not _pkg_desc['app']:
                            _pkg_desc['app'] = \
                                "/".join(_apps[_release.version])

                    # Populate package info, once for package
                    _m = _r_desc[0]["maintainer"] if _r_desc else 'n/a'
                    _all_packages[_name] = {
                        "desc": _pkg_desc,
                        "repos": _r_desc,
                        "maintainer": _m,
                        "is_mirantis": self.rm.is_mirantis(
                            _name,
                            tag=_mcp
                        ),
                        "results": {},
                        "r": _release,
                    }
                # Cross-compare versions
                _cmp = VersionCmpResult(
                    _ver_ins,
                    _ver_can,
                    _all_packages[_name]['r']
                )
                # Update results structure
                # shortcut to results
                _res = _all_packages[_name]['results']
                # update status
                if _cmp.status not in _res:
                    _res[_cmp.status] = {}
                # update action
                if _cmp.action not in _res[_cmp.status]:
                    _res[_cmp.status][_cmp.action] = {}
                # update node
                if node_name not in _res[_cmp.status][_cmp.action]:
                    _res[_cmp.status][_cmp.action][node_name] = {}
                # put result
                _res[_cmp.status][_cmp.action][node_name] = {
                    'i': _ver_ins,
                    'c': _ver_can,
                    'res': _cmp,
                    'raw': _value['raw']
                }

        self._packages = _all_packages
        _progress.end()

    def create_report(self, filename, rtype, full=None):
        """
        Create static html showing packages diff per node

        :return: buff with html
        """
        logger_cli.info("# Generating report to '{}'".format(filename))
        if rtype == 'html':
            _type = reporter.HTMLPackageCandidates()
        elif rtype == 'csv':
            _type = reporter.CSVAllPackages()
        else:
            raise ConfigException("Report type not set")
        _report = reporter.ReportToFile(
            _type,
            filename
        )
        payload = {
            "nodes": salt_master.nodes,
            "mcp_release": salt_master.mcp_release,
            "openstack_release": salt_master.openstack_release
        }
        payload.update(self.presort_packages(self._packages, full))
        _report(payload)
        logger_cli.info("-> Done")
