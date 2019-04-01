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
        with open(os.path.join(pkg_dir, 'etc', config.pkg_versions_map)) as f:
            _reader = csv.reader(f, delimiter=',')
            # load packages
            for row in _reader:
                # load release version labels
                if _reader.line_num == 1:
                    self._labels = [v for v in row[5:]]
                    continue
                # package_name,component,application_or_service,repo,openstack_release,2018.4.0,2018.11.0,2019.2.0,2019.2.1,2019.2.2
                # reassign for code readability
                _pkg = row[0]
                _component = row[1]
                _app = row[2]
                _repo = row[3]
                # if release cell empty - use keyword 'any'
                _os_release = row[4] if len(row[4]) > 0 else 'any' 

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
            #return self._dummy_desc
            return None


class DebianVersion(object):
    epoch = ""
    major = ""
    debian = ""
    status = ""
    version = ""
    def __init__(self, version_string):
        # save
        if len(version_string) < 1:
            self.epoch = None
            self.major = None
            self.debian = None
            self.version = 'n/a'
            return
        else:
            # do parse
            _v = version_string
            # colon presence, means epoch present
            _e = _v.split(':', 1)[0] if ':' in _v else ''
            # if epoch was there, major should be cut
            _m = _v if ':' not in _v else _v.split(':', 1)[1]
            # dash presence, means debian present
            _d = _m.rsplit('-', 1)[1] if '-' in _m else ''
            # if debian was there, major version should be cut
            _m = _m if '-' not in _m else _m.rsplit('-', 1)[0]

            self.epoch = _e
            self.major = _m
            self.debian = _d
            self.version = version_string
    
    def __lt__(v):
        if v.epoch and v.epoch > self.epoch:
            return True
        elif v.major and v.major > self.major:
            return True
        else:
            return False

    def __eq__(v):
        if v.epoch and v.epoch == self.epoch:
            return True
        elif v.major and v.major == self.major:
            return True
        else:
            return False

    def __gt__(v):
        if v.epoch and v.epoch < self.epoch:
            return True
        elif v.major and v.major < self.major:
            return True
        else:
            return False


class VersionStatus(object):
    _u = "upgrade"
    _d = "downgrade"
    _e = "error"

    status = ""
    source = None
    target = None

    def deb_lower(_s, _t):
        if _t.debian and _t.debian > _s.debian:
            return True
        else:
            return false
    
    def __init__(self, i, c, r):
        # compare three versions and write a result
        self.source = i

        # I < C && I = R --> upgrade (ok)
        # I.e. linked repo contains newer versions, 
        # but installed version is inline with the release version
        if i < c and i == r:
            self.status = u
            self.target = c

        # I > C && C = R --> downgrade (fail)
        # I.e. linked repo and release versions are the same,
        # but installed version is newer

        # I = C && I < R --> error
        # I.e. installed and linked repo is inline,
        # but they are lower than release

        
        # installed version epoch:major should be < to candidate
        
        # i -> c