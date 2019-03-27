import csv
import os

from cfg_checker.common import config, logger, logger_cli, pkg_dir

class PkgVersions(object):
    _labels = []
    _list = {}

    _dummy_desc = {
        "component": "",
        "app": "",
        "repo": "other",
        "versions": {}
    }

    def __init__(self):
        # preload csv file
        logger_cli.info("# Preloading MCP release versions")
        _config_path = os.path.join(pkg_dir, 'etc', _env_name + '.env')
        with open(os.path.join(pkg_dir, 'etc', config.pkg_versions_map)) as f:
            _reader = csv.reader(f, delimiter=',')
            # load release version labels
            if _reader.line_num == 1:
                self._labels = [v for v in row[5:]]
                continue
            
            # load packages
            for row in _reader:
                # package_name,component,application_or_service,repo,openstack_release,2018.4.0,2018.11.0,2019.2.0,2019.2.1,2019.2.2
                # reassign for code readability
                _pkg = row[0]
                _component = row[1]
                _app = row[2]
                _repo = row[3]
                _os_release = row[4]

                # prepare versions dict
                _l = self._labels
                _versions = {_l[i]:row[5+i] for i in range(0, len(row[5:]))}
                
                if _pkg in self._list:
                    if _os_release in self._list[_pkg]["versions"]:
                        # all pkg/os_releases should be uniq. If found, latest one used
                        logger_cli.info(
                            "-> WARNING: Duplicate package info found "
                            "'{}' (line {})".format(
                                _pkg,
                                _reader.line_num
                            )
                        )
                else:
                    # update pkg data in list
                    self._list.update({
                        _pkg: {
                            "component": _component,
                            "app": _app,
                            "repo": _repo,
                            "versions": {}
                        }
                    })
                
                # and finally, update the versions for this release
                self._list[_pkg]["versions"].update({
                    _os_release: _versions
                })
    
    def __getitem__(self, pkg_name):
        if pkg_name in self._list:        
            return self._list[pkg_name]
        else:
            return self._dummy_desc

