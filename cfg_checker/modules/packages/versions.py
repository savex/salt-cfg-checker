import csv
import os

from cfg_checker.common import config, logger, logger_cli, pkg_dir, const


class PkgVersions(object):
    _labels = []
    _list = {}

    dummy_desc = {
        "component": "unlisted",
        "app": "-",
        "repo": "-",
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
    epoch = None
    epoch_status = const.VERSION_NA
    upstream = None
    upstream_rev = None
    upstream_status = const.VERSION_NA
    debian = None
    debian_rev = None
    debian_status = const.VERSION_NA

    status = ""
    version = ""

    @staticmethod
    def split_revision(version_fragment):
        # The symbols are -, +, ~
        _symbols = ['-', '+', '~']
        # nums, coz it is faster then regex
        _chars = [46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57]
        _ord_map = [ord(ch) not in _chars for ch in version_fragment]
        # if there is nothing to extract, return at once
        if not any([_s in version_fragment for _s in _symbols]) \
            and not any(_ord_map):
            # no revisions
            return version_fragment, ""
        else:
            _main = _rev = ""
            # get indices
            _indices = []
            for _s in _symbols:
                if _s in version_fragment:
                    _indices.append(version_fragment.index(_s))
            for _s in version_fragment:
                if ord(_s) not in _chars:
                    _indices.append(version_fragment.index(_s))
            # sort indices
            _indices.sort()
            # extract starting from the lowest one
            _main = version_fragment[:_indices[0]]
            _rev = version_fragment[_indices[0]:]
            return _main, _rev
    
    def __init__(self, version_string):
        # save
        if len(version_string) < 1:
            self.epoch = None
            self.upstream = None
            self.debian = None
            self.version = 'n/a'
            return
        else:
            # do parse the main versions
            _v = version_string
            # colon presence, means epoch present
            _e = _v.split(':', 1)[0] if ':' in _v else ''
            # if epoch was there, upstream should be cut
            _m = _v if ':' not in _v else _v.split(':', 1)[1]
            # dash presence, means debian present
            _d = _m.rsplit('-', 1)[1] if '-' in _m else ''
            # if debian was there, upstream version should be cut
            _m = _m if '-' not in _m else _m.rsplit('-', 1)[0]

            self.epoch = _e
            self.upstream, self.upstream_rev = self.split_revision(_m)
            self.debian, self.debian_rev = self.split_revision(_d)
            self.version = version_string
    
    # Following functions is a freestyle python mimic of apt's upstream, enjoy
    # https://github.com/chaos/apt/blob/master/apt/apt-pkg/deb/debversion.cc#L42
    # mimic produced in order not to pull any packages or call external code
    @staticmethod
    def _cmp_fragment(lhf, rhf):
        # search for difference
        # indices
        _li = _ri = 0
        # pre-calc len
        _lL = len(lhf)
        _rL = len(rhf)
        # bool for compare found
        _diff = False
        while _li < _lL and _ri < _rL:
            # iterate lists
            _num = lhf[_li] - rhf[_ri]
            if _num:
                return _num
            _li += 1
            _ri += 1
        
        # diff found? lens equal?
        if not _diff and _lL != _rL:
            # lens not equal? Longer - later
            return _lL - _rL
        else:
            # equal
            return 0
    
    def _cmp_num(self, lf, rf):
        # split fragments into lists
        _lhf = lf.split('.') if '.' in lf else list(lf)
        _rhf = rf.split('.') if '.' in rf else list(rf)
        # cast them to ints, delete empty strs
        _lhf = [int(n) for n in _lhf if len(n)]
        _rhf = [int(n) for n in _rhf if len(n)]

        return self._cmp_fragment(_lhf, _rhf)
    
    def _cmp_lex(self, lf, rf):
        # cast each item into its ORD value
        _lhf = [ord(n) for n in lf]
        _rhf = [ord(n) for n in rf]

        return self._cmp_fragment(_lhf, _rhf)        
   # end of cmps

    # main part compared using splitted numbers
    # if equal, revision is compared using lexical comparizon
    def __lt__(self, v):
        if self._cmp_num(self.epoch, v.epoch) < 0:
            return True
        elif self._cmp_num(self.upstream, v.upstream) < 0:
            return True
        elif self._cmp_lex(self.upstream_rev, v.upstream_rev) < 0:
            return True
        else:
            return False

    def __eq__(self, v):
        # compare all portions
        _result = []
        _result.append(self._cmp_num(self.epoch, v.epoch))
        _result.append(self._cmp_num(self.upstream, v.upstream))
        _result.append(self._cmp_lex(self.upstream_rev, v.upstream_rev))
        # if there is any non-zero, its not equal
        return not any(_result)

    def __gt__(self, v):
        if self._cmp_num(self.epoch, v.epoch) > 0:
            return True
        elif self._cmp_num(self.upstream, v.upstream) > 0:
            return True
        elif self._cmp_lex(self.upstream_rev, v.upstream_rev) > 0:
            return True
        else:
            return False
    
    def update_parts(self, target, status):
        # updating parts of version statuses
        if self._cmp_num(self.epoch, target.epoch) != 0:
            self.epoch_status = status
        else:
            self.epoch_status = const.VERSION_OK

        if self._cmp_num(self.upstream, target.upstream) != 0 \
            or self._cmp_lex(self.upstream_rev, target.upstream_rev) != 0:
            self.upstream_status = status
        else:
            self.upstream_status = const.VERSION_OK

        if self._cmp_lex(self.debian, target.debian) != 0 \
            or self._cmp_lex(self.debian_rev, target.debian_rev) != 0:
            self.debian_status = status
        else:
            self.debian_status = const.VERSION_OK


class VersionCmpResult(object):
    status = ""
    action = ""

    source = None
    target = None


    def __init__(self, i, c, r):
        # compare three versions and write a result
        self.source = i
        self.status = const.VERSION_NA
        self.action = const.ACT_NA
        
        # Check if there is a release version present
        if r and len(r.version) > 0 and r.version != 'n/a':
            # I < C, installed version is older
            if i < c:
                self.target = c
                if i == r:
                    # installed version is equal vs release version
                    self.status = const.VERSION_OK
                    self.action = const.ACT_UPGRADE
                elif i > r:
                    # installed version is newer vs release version
                    self.status = const.VERSION_UP
                    self.action = const.ACT_UPGRADE
                elif i < r and r < c:
                    # installed version is older vs release version
                    self.status = const.VERSION_ERR
                    self.action = const.ACT_NEED_UP
                    self.target = r
                elif i < r and c == r:
                    # installed version is older vs release version
                    self.status = const.VERSION_ERR
                    self.action = const.ACT_NEED_UP
                    self.target = c
                elif c < r:
                    # installed and repo versions older vs release version
                    self.status = const.VERSION_ERR
                    self.action = const.ACT_REPO
            # I > C
            # installed version is newer
            elif i > c:
                self.target = c
                if c == r:
                    # some unknown version installed
                    self.status = const.VERSION_ERR
                    self.action = const.ACT_NEED_DOWN
                elif c > r:
                    # installed and repo versions newer than release
                    self.status = const.VERSION_UP
                    self.action = const.ACT_NEED_DOWN
                elif c < r and r < i:
                    # repo is older vs release and both older vs installed
                    self.status = const.VERSION_UP
                    self.action = const.ACT_REPO
                elif c < r and r == i:
                    # repo is older vs release, but release version installed
                    self.status = const.VERSION_OK
                    self.action = const.ACT_REPO
                elif i < r:
                    # both repo and installed older vs release, new target
                    self.status = const.VERSION_DOWN
                    self.action = const.ACT_REPO
                    self.target = r
            # I = C
            # installed and linked repo is inline,
            elif i == c:
                self.target = c
                if i < r:
                    # both are old, new target
                    self.status = const.VERSION_ERR
                    self.action = const.ACT_REPO
                    self.target = r
                elif i > r:
                    # both are newer, same target
                    self.status = const.VERSION_UP
                    self.action = const.ACT_NA
                elif i == r:
                    # all is ok
                    self.status = const.VERSION_OK
                    self.action = const.ACT_NA
        else:
            # no release version present
            self.target = c
            if i < c:
                self.status = const.VERSION_OK
                self.action = const.ACT_UPGRADE
            elif i > c:
                self.status = const.VERSION_UP
                self.action = const.ACT_NEED_DOWN
            elif i == c:
                self.status = const.VERSION_OK
                self.action = const.ACT_NA
        
        # and we need to update per-part status
        self.source.update_parts(self.target, self.status)

    @staticmethod
    def deb_lower(_s, _t):
        if _t.debian and _t.debian > _s.debian:
            return True
        else:
            return false
