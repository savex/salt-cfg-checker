import json
import os
import re
from copy import deepcopy

from cfg_checker.common import logger, logger_cli, nested_set
from cfg_checker.common.const import _mainteiners_index_filename
from cfg_checker.common.const import _mirantis_versions_filename
from cfg_checker.common.const import _other_versions_filename
from cfg_checker.common.const import _pkg_desc_archive
from cfg_checker.common.const import _repos_index_filename
from cfg_checker.common.const import _repos_info_archive
from cfg_checker.common.const import _repos_versions_archive
from cfg_checker.common.const import ubuntu_releases
from cfg_checker.common.file_utils import ensure_folder_exists
from cfg_checker.common.file_utils import get_gzipped_file
from cfg_checker.common.settings import pkg_dir
from cfg_checker.helpers.console_utils import Progress
from cfg_checker.helpers.tgz import TGZFile

import requests
from requests.exceptions import ConnectionError

ext = ".json"


def get_tag_label(_tag, parsed=False):
    # prettify the tag for printing
    if parsed:
        _label = "+ "
    else:
        _label = "  "

    if _tag.endswith(".update"):
        _label += "[updates] " + _tag.rsplit('.', 1)[0]
    elif _tag.endswith(".hotfix"):
        _label += " [hotfix] " + _tag.rsplit('.', 1)[0]
    else:
        _label += " "*10 + _tag

    return _label


def _get_value_index(_di, value, header=None):
    # Mainteiner names often uses specific chars
    # so make sure that value saved is str not str
    # Python2
    # _val = str(value, 'utf-8') if isinstance(value, str) else value
    # Python3 has always utf-8 decoded value
    _val = value
    if header:
        try:
            _ = next(filter(lambda i: _di[i]["header"] == header, _di))
            # iterator not empty, find index
            for _k, _v in _di.items():
                if _v["header"] == header:
                    _index = _k
        except StopIteration:
            _index = str(len(_di.keys()) + 1)
            _di[_index] = {
                "header": header,
                "props": _val
            }
        finally:
            return _index
    else:
        try:
            _ = next(filter(lambda i: _di[i] == _val, _di))
            # iterator not empty, find index
            for _k, _v in _di.items():
                if _v == _val:
                    _index = _k
        except StopIteration:
            _index = str(len(_di.keys()) + 1)
            # on save, cast it as str
            _di[_index] = _val
        finally:
            return _index


def _safe_load(_f, _a):
    if _f in _a.list_files():
        logger_cli.debug(
            "... loading '{}':'{}'".format(
                _a.basefile,
                _f
            )
        )
        return json.loads(_a.get_file(_f, decode=True))
    else:
        return {}


def _n_url(url):
    if url[-1] == '/':
        return url
    else:
        return url + '/'


class ReposInfo(object):
    init_done = False

    def _init_vars(self):
        self.repos = []

    def _init_folders(self, arch_folder=None):
        if arch_folder:
            self._arch_folder = arch_folder
            self._repofile = os.path.join(arch_folder, _repos_info_archive)
        else:
            self._arch_folder = os.path.join(pkg_dir, "versions")
            self._repofile = os.path.join(
                self._arch_folder,
                _repos_info_archive
            )

    def __init__(self, arch_folder=None):
        # perform inits
        self._init_vars()
        self._init_folders(arch_folder)
        self.init_done = True

    def __call__(self, *args, **kwargs):
        if self.init_done:
            return self
        else:
            return self.__init__(self, *args, **kwargs)

    @staticmethod
    def _ls_repo_page(url):
        # Yes, this is ugly. But it works ok for small HTMLs.
        _a = "<a"
        _s = "href="
        _e = "\">"
        try:
            page = requests.get(url, timeout=60)
        except ConnectionError as e:
            logger_cli.error("# ERROR: {}".format(e.message))
            return [], []
        a = page.text.splitlines()
        # Comprehension for dirs. Anchors for ends with '-'
        _dirs = [l[l.index(_s)+6:l.index(_e)-1]
                 for l in a if l.startswith(_a) and l.endswith('-')]
        # Comprehension for files. Anchors ends with size
        _files = [l[l.index(_s)+6:l.index(_e)]
                  for l in a if l.startswith(_a) and not l.endswith('-')]

        return _dirs, _files

    def search_pkg(self, url, _list):
        # recoursive method to walk dists tree
        _dirs, _files = self._ls_repo_page(url)

        for _d in _dirs:
            # Search only in dists, ignore the rest
            if "dists" not in url and _d != "dists":
                continue
            _u = _n_url(url + _d)
            self.search_pkg(_u, _list)

        for _f in _files:
            if _f == "Packages.gz":
                _list.append(url + _f)
                logger.debug("... [F] '{}'".format(url + _f))

        return _list

    @staticmethod
    def _map_repo(_path_list, _r):
        for _pkg_path in _path_list:
            _l = _pkg_path.split('/')
            _kw = _l[_l.index('dists')+1:]
            _kw.reverse()
            _repo_item = {
                "arch": _kw[1][7:] if "binary" in _kw[1] else _kw[1],
                "type": _kw[2],
                "ubuntu-release": _kw[3],
                "filepath": _pkg_path
            }
            _r.append(_repo_item)

    def _find_tag(self, _t, _u, label=""):
        if label:
            _url = _n_url(_u + label)
            _label = _t + '.' + label
        else:
            _url = _u
            _label = _t
        _ts, _ = self._ls_repo_page(_url)
        if _t in _ts:
            logger.debug(
                "... found tag '{}' at '{}'".format(
                    _t,
                    _url
                )
            )
            return {
                _label: {
                    "baseurl": _n_url(_url + _t),
                    "all": {}
                }
            }
        else:
            return {}

    def fetch_repos(self, url, tag=None):
        base_url = _n_url(url)
        logger_cli.info("# Using '{}' as a repos source".format(base_url))

        logger_cli.info("# Gathering repos info (i.e. links to 'packages.gz')")
        # init repoinfo archive
        _repotgz = TGZFile(self._repofile)
        # prepare repo links
        _repos = {}
        if tag:
            # only one tag to process
            _repos.update(self._find_tag(tag, base_url))
            _repos.update(self._find_tag(tag, base_url, label="hotfix"))
            _repos.update(self._find_tag(tag, base_url, label="update"))
        else:
            # gather all of them
            _tags, _ = self._ls_repo_page(base_url)
            if "hotfix" in _tags:
                _tags.remove('hotfix')
            if "update" in _tags:
                _tags.remove('update')
            # search tags in subfolders
            _h_tags, _ = self._ls_repo_page(base_url + 'hotfix')
            _u_tags, _ = self._ls_repo_page(base_url + 'update')
            _tags.extend([t for t in _h_tags if t not in _tags])
            _tags.extend([t for t in _u_tags if t not in _tags])
            _progress = Progress(len(_tags))
            _index = 0
            for _tag in _tags:
                _repos.update(self._find_tag(_tag, base_url))
                _repos.update(self._find_tag(_tag, base_url, label="hotfix"))
                _repos.update(self._find_tag(_tag, base_url, label="update"))
                _index += 1
                _progress.write_progress(_index)
            _progress.end()

        # parse subtags
        for _label in _repos.keys():
            logger_cli.info("-> processing tag '{}'".format(_label))
            _name = _label + ".json"
            if _repotgz.has_file(_name):
                logger_cli.info(
                    "-> skipping, '{}' already has '{}'".format(
                        _repos_info_archive,
                        _name
                    )
                )
                continue
            # process the tag
            _repo = _repos[_label]
            _baseurl = _repos[_label]["baseurl"]
            # get the subtags
            _sub_tags, _ = self._ls_repo_page(_baseurl)
            _total_index = len(_sub_tags)
            _index = 0
            _progress = Progress(_total_index)
            logger.debug(
                "... found {} subtags for '{}'".format(
                    len(_sub_tags),
                    _label
                )
            )
            # save the url and start search
            for _stag in _sub_tags:
                _u = _baseurl + _stag
                _index += 1
                logger.debug(
                    "... searching repos in '{}/{}'".format(
                        _label,
                        _stag
                    )
                )

                # Searching Package collections
                if _stag in ubuntu_releases:
                    # if stag is the release, this is all packages
                    _repo["all"][_stag] = []
                    _repo["all"]["url"] = _n_url(_u)
                    _path_list = self.search_pkg(_n_url(_u), [])
                    self._map_repo(_path_list, _repo["all"][_stag])
                    logger.info(
                        "-> found {} dists".format(
                            len(_repo["all"][_stag])
                        )
                    )

                else:
                    # each subtag might have any ubuntu release
                    # so iterate them
                    _repo[_stag] = {
                        "url": _n_url(_u)
                    }
                    _releases, _ = self._ls_repo_page(_n_url(_u))
                    for _rel in _releases:
                        if _rel not in ubuntu_releases:
                            logger.debug(
                                "... skipped unknown ubuntu release: "
                                "'{}' in '{}'".format(
                                    _rel,
                                    _u
                                )
                            )
                        else:
                            _rel_u = _n_url(_u) + _rel
                            _repo[_stag][_rel] = []
                            _path_list = self.search_pkg(_n_url(_rel_u), [])
                            self._map_repo(
                                _path_list,
                                _repo[_stag][_rel]
                            )
                            logger.info(
                                "-> found {} dists for '{}'".format(
                                    len(_repo[_stag][_rel]),
                                    _rel
                                )
                            )
                _progress.write_progress(_index)

            _progress.end()
            _name = _label + ext
            _repotgz.add_file(_name, buf=json.dumps(_repo, indent=2))
            logger_cli.info(
                "-> archive '{}' updated with '{}'".format(
                    self._repofile,
                    _name
                )
            )

        return

    def list_tags(self, splitted=False):
        _files = TGZFile(self._repofile).list_files()
        # all files in archive with no '.json' part
        _all = set([f.rsplit('.', 1)[0] for f in _files])
        if splitted:
            # files that ends with '.update'
            _updates = set([f for f in _all if f.find('update') >= 0])
            # files that ends with '.hotfix'
            _hotfix = set([f for f in _all if f.find('hotfix') >= 0])
            # remove updates and hotfix tags from all. The true magic of SETs
            _all = _all - _updates - _hotfix
            # cut updates and hotfix endings
            _updates = [f.rsplit('.', 1)[0] for f in _updates]
            _hotfix = [f.rsplit('.', 1)[0] for f in _hotfix]

            return _all, _updates, _hotfix
        else:
            # dynamic import
            import re
            _all = list(_all)
            # lexical tags
            _lex = [s for s in _all if not s[0].isdigit()]
            _lex.sort()
            # tags with digits
            _dig = [s for s in _all if s[0].isdigit()]
            _dig = sorted(
                _dig,
                key=lambda x: tuple(int(i) for i in re.findall(r"\d+", x)[:3])
            )

            return _dig + _lex

    def get_repoinfo(self, tag):
        _tgz = TGZFile(self._repofile)
        _buf = _tgz.get_file(tag + ext, decode=True)
        return json.loads(_buf)


class RepoManager(object):
    init_done = False

    def _init_folders(self, arch_folder=None):
        # overide arch folder if needed
        if arch_folder:
            self._arch_folder = arch_folder
        else:
            self._arch_folder = os.path.join(pkg_dir, "versions")

        self._versions_arch = os.path.join(
            self._arch_folder,
            _repos_versions_archive
        )
        self._desc_arch = os.path.join(self._arch_folder, _pkg_desc_archive)

    def _init_vars(self, info_class):
        # RepoInfo instance init
        if info_class:
            self._info_class = info_class
        else:
            self._info_class = ReposInfo()
        # archives
        self._apps_filename = "apps.json"

        # repository index
        self._repo_index = {}
        self._mainteiners_index = {}

        self._apps = {}

        # init package versions storage
        self._versions_mirantis = {}
        self._versions_other = {}

    def _init_archives(self):
        # Init version files
        self.versionstgz = TGZFile(
            self._versions_arch,
            label="MCP Configuration Checker: Package versions archive"
        )
        self.desctgz = TGZFile(
            self._desc_arch,
            label="MCP Configuration Checker: Package descriptions archive"
        )

        # section / app
        self._apps = _safe_load(
            self._apps_filename,
            self.desctgz
        )

        # indices
        self._repo_index = _safe_load(
            _repos_index_filename,
            self.versionstgz
        )
        self._mainteiners_index = _safe_load(
            _mainteiners_index_filename,
            self.versionstgz
        )

        # versions
        self._versions_mirantis = _safe_load(
            _mirantis_versions_filename,
            self.versionstgz
        )
        self._versions_other = _safe_load(
            _other_versions_filename,
            self.versionstgz
        )

    def __init__(self, arch_folder=None, info_class=None):
        # Perform inits
        self._init_vars(info_class)
        self._init_folders(arch_folder)
        # Ensure that versions folder exists
        logger_cli.debug(ensure_folder_exists(self._arch_folder))
        # Preload/create archives
        self._init_archives()
        self.init_done = True

    def __call__(self, *args, **kwargs):
        if self.init_done:
            return self
        else:
            return self.__init__(self, *args, **kwargs)

    def _create_repo_header(self, p):
        _header = "_".join([
            p['tag'],
            p['subset'],
            p['release'],
            p['ubuntu-release'],
            p['type'],
            p['arch']
        ])
        return _get_value_index(self._repo_index, p, header=_header)

    def _get_indexed_values(self, pair):
        _h, _m = pair.split('-')
        return self._repo_index[_h], self._mainteiners_index[_m]

    def _update_pkg_version(self, _d, n, v, md5, s, a, h_index, m_index):
        """Method updates package version record in global dict
        """
        # 'if'*4 operation is pretty expensive when using it 100k in a row
        # so try/except is a better way to go, even faster than 'reduce'
        _pair = "-".join([h_index, m_index])
        _info = {
            'repo': [_pair],
            'section': s,
            'app': a
        }
        try:
            # try to load list
            _list = _d[n][v][md5]['repo']
            # cast it as set() and union()
            _list = set(_list).union([_pair])
            # cast back as set() is not serializeable
            _d[n][v][md5]['repo'] = list(_list)
            return False
        except KeyError:
            # ok, this is fresh pkg. Do it slow way.
            if n in _d:
                # there is such pkg already
                if v in _d[n]:
                    # there is such version, check md5
                    if md5 in _d[n][v]:
                        # just add new repo header
                        if _pair not in _d[n][v][md5]['repo']:
                            _d[n][v][md5]['repo'].append(_pair)
                    else:
                        # check if such index is here...
                        _existing = filter(
                            lambda i: _pair in _d[n][v][i]['repo'],
                            _d[n][v]
                        )
                        if _existing:
                            # Yuck! Same version had different MD5
                            _r, _m = self._get_indexed_values(_pair)
                            logger_cli.error(
                                "# ERROR: Package version has multiple MD5s "
                                "in '{}': {}:{}:{}".format(
                                    _r,
                                    n,
                                    v,
                                    md5
                                )
                            )
                        _d[n][v][md5] = _info
                else:
                    # this is new version for existing package
                    _d[n][v] = {
                        md5: _info
                    }
                return False
            else:
                # this is new pakcage
                _d[n] = {
                    v: {
                        md5: _info
                    }
                }
                return True

    def _save_repo_descriptions(self, repo_props, desc):
        # form the filename for the repo and save it
        self.desctgz.add_file(
            self._create_repo_header(repo_props),
            json.dumps(desc)
        )

    # def get_description(self, repo_props, name, md5=None):
    #     """Gets target description
    #     """
    #     _filename = self._create_repo_header(repo_props)
    #     # check if it is present in cache
    #     if _filename in self._desc_cache:
    #         _descs = self._desc_cache[_filename]
    #     else:
    #         # load data
    #         _descs = self.desctgz.get_file(_filename)
    #         # Serialize it
    #         _descs = json.loads(_descs)
    #         self._desc_cache[_filename] = _descs
    #     # return target desc
    #     if name in _descs and md5 in _descs[name]:
    #         return _descs[name][md5]
    #     else:
    #         return None

    def parse_tag(self, tag, descriptions=False, apps=False):
        """Download and parse Package.gz files for specific tag
        By default, descriptions not saved
        due to huge resulting file size and slow processing
        """
        # init gzip and downloader
        _info = self._info_class.get_repoinfo(tag)
        # calculate Packages.gz files to process
        _baseurl = _info.pop("baseurl")
        _total_components = len(_info.keys()) - 1
        _ubuntu_package_repos = 0
        _other_repos = 0
        for _c, _d in _info.items():
            for _ur, _l in _d.items():
                if _ur in ubuntu_releases:
                    _ubuntu_package_repos += len(_l)
                elif _ur != 'url':
                    _other_repos += len(_l)
        logger_cli.info(
            "-> loaded repository info for '{}'.\n"
            "  '{}', {} components, {} ubuntu repos, {} other/uknown".format(
                _baseurl,
                tag,
                _total_components,
                _ubuntu_package_repos,
                _other_repos
            )
        )
        # init progress bar
        _progress = Progress(_ubuntu_package_repos)
        _index = 0
        _processed = 0
        _new = 0
        for _c, _d in _info.items():
            # we do not need url here, just get rid of it
            if 'url' in _d:
                _d.pop('url')
            # _url =  if 'url' in _d else _baseurl + _c
            for _ur, _l in _d.items():
                # iterate package collections
                for _p in _l:
                    # descriptions
                    if descriptions:
                        _descriptions = {}
                    # download and unzip
                    _index += 1
                    _progress.write_progress(
                        _index,
                        note="/ {} {} {} {} {}, GET 'Packages.gz'".format(
                            _c,
                            _ur,
                            _p['ubuntu-release'],
                            _p['type'],
                            _p['arch']
                        )
                    )
                    _raw = get_gzipped_file(_p['filepath'])
                    if not _raw:
                        # empty repo...
                        _progress.clearline()
                        logger_cli.warning(
                            "# WARNING: Empty file: '{}'".format(
                                _p['filepath']
                            )
                        )
                        continue
                    else:
                        _raw = _raw.decode("utf-8")
                    _progress.write_progress(
                        _index,
                        note="/ {} {} {} {} {}, {}/{}".format(
                            _c,
                            _ur,
                            _p['ubuntu-release'],
                            _p['type'],
                            _p['arch'],
                            _processed,
                            _new
                        )
                    )
                    _lines = _raw.splitlines()
                    # break lines collection into isolated pkg data
                    _pkg = {
                        "tag": tag,
                        "subset": _c,
                        "release": _ur
                    }
                    _pkg.update(_p)
                    _desc = {}
                    _key = _value = ""
                    # if there is no empty line at end, add it
                    if _lines[-1] != '':
                        _lines.append('')
                    # Process lines
                    for _line in _lines:
                        if not _line:
                            # if the line is empty, process pkg data gathered
                            _name = _desc['package']
                            _md5 = _desc['md5sum']
                            _version = _desc['version']
                            _mainteiner = _desc['maintainer']

                            if 'source' in _desc:
                                _ap = _desc['source'].lower()
                            else:
                                _ap = "-"

                            if apps:
                                # insert app
                                _sc = _desc['section'].lower()
                                if 'source' in _desc:
                                    _ap = _desc['source'].lower()
                                else:
                                    _ap = "-"

                                try:
                                    _tmp = set(self._apps[_sc][_ap][_name])
                                    _tmp.add(_desc['architecture'])
                                    self._apps[_sc][_ap][_name] = list(_tmp)
                                except KeyError:
                                    nested_set(
                                        self._apps,
                                        [_sc, _ap, _name],
                                        [_desc['architecture']]
                                    )

                            # Check is mainteiner is Mirantis
                            if _mainteiner.endswith("@mirantis.com>"):
                                # update mirantis versions
                                if self._update_pkg_version(
                                    self._versions_mirantis,
                                    _name,
                                    _version,
                                    _md5,
                                    _desc['section'].lower(),
                                    _ap,
                                    self._create_repo_header(_pkg),
                                    _get_value_index(
                                        self._mainteiners_index,
                                        _mainteiner
                                    )
                                ):
                                    _new += 1
                            else:
                                # update other versions
                                if self._update_pkg_version(
                                    self._versions_other,
                                    _name,
                                    _version,
                                    _md5,
                                    _desc['section'].lower(),
                                    _ap,
                                    self._create_repo_header(_pkg),
                                    _get_value_index(
                                        self._mainteiners_index,
                                        _mainteiner
                                    )
                                ):
                                    _new += 1

                            if descriptions:
                                _d_new = {
                                    _md5: deepcopy(_desc)
                                }
                                try:
                                    _descriptions[_name].update(_d_new)
                                except KeyError:
                                    _descriptions[_name] = _d_new
                            # clear the data for next pkg
                            _processed += 1
                            _desc = {}
                            _key = ""
                            _value = ""
                        elif _line.startswith(' '):
                            _desc[_key] += "\n{}".format(_line)
                        else:
                            _key, _value = _line.split(': ', 1)
                            _key = _key.lower()

                            _desc[_key] = _value
                    # save descriptions if needed
                    if descriptions:
                        _progress.clearline()
                        self._save_repo_descriptions(_pkg, _descriptions)

        _progress.end()
        # backup headers to disk
        self.versionstgz.add_file(
            _repos_index_filename,
            json.dumps(self._repo_index),
            replace=True
        )
        self.versionstgz.add_file(
            _mainteiners_index_filename,
            json.dumps(self._mainteiners_index),
            replace=True
        )
        if apps:
            self.desctgz.add_file(
                self._apps_filename,
                json.dumps(self._apps),
                replace=True
            )

        return

    def fetch_versions(self, tag, descriptions=False, apps=False):
        """Executes parsing for specific tag
        """
        if descriptions:
            logger_cli.warning(
                "\n\n# !!! WARNING: Saving repo descriptions "
                "consumes huge amount of disk space\n\n"
            )
        # if there is no such tag, parse it from repoinfo
        logger_cli.info("# Fetching versions for {}".format(tag))
        self.parse_tag(tag, descriptions=descriptions, apps=apps)
        logger_cli.info("-> saving updated versions")
        self.versionstgz.add_file(
            _mirantis_versions_filename,
            json.dumps(self._versions_mirantis),
            replace=True
        )
        self.versionstgz.add_file(
            _other_versions_filename,
            json.dumps(self._versions_other),
            replace=True
        )

    def build_repos(self, url, tag=None):
        """Builds versions data for selected tag, or for all of them
        """
        # recoursively walk the mirrors
        # and gather all of the repos for 'tag' or all of the tags
        self._info_class.fetch_repos(url, tag=tag)

    def _build_action(self, url, tags):
        for t in tags:
            logger_cli.info("# Building repo info for '{}'".format(t))
            self.build_repos(url, tag=t)

    def get_available_tags(self, tag=None):
        # Populate action tags
        major, updates, hotfix = self._info_class.list_tags(splitted=True)

        _tags = []
        if tag in major:
            _tags.append(tag)
        if tag in updates:
            _tags.append(tag + ".update")
        if tag in hotfix:
            _tags.append(tag + ".hotfix")

        return _tags

    def action_for_tag(
        self,
        url,
        tag,
        action=None,
        descriptions=None,
        apps=None
    ):
        """Executes action for every tag from all collections
        """
        if not action:
            logger_cli.info("# No action set, nothing to do")
        # See if this is a list action
        if action == "list":
            _all = self._info_class.list_tags()
            if _all:
                # Print pretty list and exit
                logger_cli.info("# Tags available at '{}':".format(url))
                for t in _all:
                    _ri = self._repo_index
                    _isparsed = any(
                        [k for k, v in _ri.items()
                         if v['props']['tag'] == t]
                    )
                    if _isparsed:
                        logger_cli.info(get_tag_label(t, parsed=True))
                    else:
                        logger_cli.info(get_tag_label(t))
            else:
                logger_cli.info("# Not tags parsed yet for '{}':".format(url))

            # exit
            return

        if action == "build":
            self._build_action(url, [tag])

        # Populate action tags
        _action_tags = self.get_available_tags(tag)

        if not _action_tags:
            logger_cli.info(
                "# Tag of '{}' not found. "
                "Consider rebuilding repos info.".format(tag)
            )
        else:
            logger_cli.info(
                "-> tags to process: {}".format(
                    ", ".join(_action_tags)
                )
            )
        # Execute actions
        if action == "fetch":
            for t in _action_tags:
                self.fetch_versions(t, descriptions=descriptions, apps=apps)

        logger_cli.info("# Done.")

    def show_package(self, name):
        # get the package data
        _p = self.get_package_versions(name)
        if not _p:
            logger_cli.warning(
                "# WARNING: Package '{}' not found".format(name)
            )
        else:
            # print package info using sorted tags from headers
            # Package: name
            # [u/h] tag \t <version>
            #           \t <version>
            # <10symbols> \t <md5> \t sorted headers with no tag
            # ...
            # section
            for _s in sorted(_p):
                # app
                for _a in sorted(_p[_s]):
                    _o = ""
                    _mm = []
                    # get and sort tags
                    for _v in sorted(_p[_s][_a]):
                        _o += "\n" + " "*8 + _v + ':\n'
                        # get and sort tags
                        for _md5 in sorted(_p[_s][_a][_v]):
                            _o += " "*16 + _md5 + "\n"
                            # get and sort repo headers
                            for _r in sorted(_p[_s][_a][_v][_md5]):
                                _o += " "*24 + _r.replace('_', ' ') + '\n'
                                _m = _p[_s][_a][_v][_md5][_r]["maintainer"]
                                if _m not in _mm:
                                    _mm.append(_m)

                    logger_cli.info(
                        "\n# Package: {}/{}/{}\nMaintainers: {}".format(
                            _s,
                            _a,
                            name,
                            ", ".join(_mm)
                        )
                    )

                    logger_cli.info(_o)

    @staticmethod
    def get_apps(versions, name):
        _all = True if name == '*' else False
        _s_max = _a_max = _p_max = _v_max = 0
        _rows = []
        for _p in versions.keys():
            _vs = versions[_p]
            for _v, _d1 in _vs.items():
                for _md5, _info in _d1.items():
                    if _all or name == _info['app']:
                        _s_max = max(len(_info['section']), _s_max)
                        _a_max = max(len(_info['app']), _a_max)
                        _p_max = max(len(_p), _p_max)
                        _v_max = max(len(_v), _v_max)
                        _rows.append([
                            _info['section'],
                            _info['app'],
                            _p,
                            _v,
                            _md5,
                            len(_info['repo'])
                        ])
        # format columns
        # section
        _fmt = "{:"+str(_s_max)+"} "
        # app
        _fmt += "{:"+str(_a_max)+"} "
        # package name
        _fmt += "{:"+str(_p_max)+"} "
        # version
        _fmt += "{:"+str(_v_max)+"} "
        # md5 and number of repos is fixed
        _fmt += "{} in {} repos"

        # fill rows
        _rows = [_fmt.format(s, a, p, v, m, l) for s, a, p, v, m, l in _rows]
        _rows.sort()
        return _rows

    def show_app(self, name):
        c = 0
        rows = self.get_apps(self._versions_mirantis, name)
        if rows:
            logger_cli.info("\n# Mirantis packages for '{}'".format(name))
            logger_cli.info("\n".join(rows))
            c += 1
        rows = self.get_apps(self._versions_other, name)
        if rows:
            logger_cli.info("\n# Other packages for '{}'".format(name))
            logger_cli.info("\n".join(rows))
            c += 1
        if c == 0:
            logger_cli.info("\n# No app found for '{}'".format(name))

    def get_mirantis_pkg_names(self):
        # Mirantis maintainers only
        return set(
            self._versions_mirantis.keys()
        ) - set(
            self._versions_other.keys()
        )

    def get_other_pkg_names(self):
        # Non-mirantis Maintainers
        return set(
            self._versions_other.keys()
        ) - set(
            self._versions_mirantis.keys()
        )

    def get_mixed_pkg_names(self):
        # Mixed maintainers
        return set(
            self._versions_mirantis.keys()
        ).intersection(set(
            self._versions_other.keys()
        ))

    def is_mirantis(self, name, tag=None):
        """Method checks if this package is mainteined
        by mirantis in target tag repo
        """
        if name in self._versions_mirantis:
            # check tag
            if tag:
                _pkg = self.get_package_versions(
                    name,
                    tagged=True
                )
                _tags = []
                for s in _pkg.keys():
                    for a in _pkg[s].keys():
                        for t in _pkg[s][a].keys():
                            _tags.append(t)
                if any([t.startswith(tag) for t in _tags]):
                    return True
                else:
                    return None
            else:
                return True
        elif name in self._versions_other:
            # check tag
            if tag:
                _pkg = self.get_package_versions(
                    name,
                    tagged=True
                )
                _tags = []
                for s in _pkg.keys():
                    for a in _pkg[s].keys():
                        for t in _pkg[s][a].keys():
                            _tags.append(t)
                if any([t.startswith(tag) for t in _tags]):
                    return False
                else:
                    return None
            else:
                return False
        else:
            logger.error(
                "# ERROR: package '{}' not found "
                "while determining maintainer".format(
                    name
                )
            )
            return None

    def get_filtered_versions(
        self,
        name,
        tag=None,
        include=None,
        exclude=None
    ):
        """Method gets all the versions for the package
        and filters them using keys above
        """
        if tag:
            tag = str(tag) if not isinstance(tag, str) else tag
        _out = {}
        _vs = self.get_package_versions(name, tagged=True)
        # iterate to filter out keywords
        for s, apps in _vs.items():
            for a, _tt in apps.items():
                for t, vs in _tt.items():
                    # filter tags
                    if tag and t != tag and t.rsplit('.', 1)[0] != tag:
                        continue
                    # Skip hotfix tag
                    if t == tag + ".hotfix":
                        continue
                    for v, rp in vs.items():
                        for h, p in rp.items():
                            # filter headers with all keywords matching
                            _h = re.split(r"[\-\_]+", h)
                            _included = all([kw in _h for kw in include])
                            _excluded = any([kw in _h for kw in exclude])
                            if not _included or _excluded:
                                continue
                            else:
                                nested_set(_out, [s, a, v], [])
                                _dat = {
                                    "header": h
                                }
                                _dat.update(p)
                                _out[s][a][v].append(_dat)
        return _out

    def get_package_versions(self, name, tagged=False):
        """Method builds package version structure
        with repository properties included
        """
        # get data
        _vs = {}

        if name in self._versions_mirantis:
            _vs.update(self._versions_mirantis[name])
        if name in self._versions_other:
            _vs.update(self._versions_other[name])

        # insert repo data, insert props into headers place
        _package = {}
        if tagged:
            for _v, _d1 in _vs.items():
                # use tag as a next step
                for _md5, _info in _d1.items():
                    _s = _info['section']
                    _a = _info['app']
                    for _pair in _info['repo']:
                        _rp = {}
                        # extract props for a repo
                        _r, _m = self._get_indexed_values(_pair)
                        # get tag
                        _tag = _r["props"]["tag"]
                        # cut tag from the header
                        _cut_head = _r["header"].split("_", 1)[1]
                        # populate dict
                        _rp["maintainer"] = _m
                        _rp["md5"] = _md5
                        _rp.update(_r["props"])
                        nested_set(
                            _package,
                            [_s, _a, _tag, _v, _cut_head],
                            _rp
                        )
        else:
            for _v, _d1 in _vs.items():
                for _md5, _info in _d1.items():
                    _s = _info['section']
                    _a = _info['app']
                    for _pair in _info['repo']:
                        _r, _m = self._get_indexed_values(_pair)
                        _info["maintainer"] = _m
                        _info.update(_r["props"])
                        nested_set(
                            _package,
                            [_s, _a, _v, _md5, _r["header"]],
                            _info
                        )

        return _package

    def parse_repos(self):
        # all tags to check
        major, updates, hotfix = self._info_class.list_tags(splitted=True)

        # major tags
        logger_cli.info("# Processing major tags")
        for _tag in major:
            self.fetch_versions(_tag)

        # updates tags
        logger_cli.info("# Processing update tags")
        for _tag in updates:
            self.fetch_versions(_tag + ".update")

        # hotfix tags
        logger_cli.info("# Processing hotfix tags")
        for _tag in hotfix:
            self.fetch_versions(_tag + ".hotfix")
