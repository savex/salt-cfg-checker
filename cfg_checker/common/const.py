"""Constants that is not to be changed and used in all other files
"""

from __future__ import absolute_import, print_function

import itertools

_cnt = itertools.count()
NODE_DOWN = next(_cnt)
NODE_UP = next(_cnt)
NODE_SKIP = next(_cnt)

# version const order is important!
# biggest get shown in report top row
VERSION_NA = next(_cnt)
VERSION_OK = next(_cnt)
VERSION_UP = next(_cnt)
VERSION_DOWN = next(_cnt)
VERSION_WARN = next(_cnt)
VERSION_ERR = next(_cnt)

# action const order is important!
# biggest get shown in report top row
ACT_NA = next(_cnt)
ACT_UPGRADE = next(_cnt)
ACT_NEED_UP = next(_cnt)
ACT_NEED_DOWN = next(_cnt)
ACT_REPO = next(_cnt)

del _cnt

all_actions = {
    ACT_UPGRADE: "upgrade possible",
    ACT_NEED_UP: "needs upgrade",
    ACT_NEED_DOWN: "needs downgrade",
    ACT_REPO: "repo update",
    ACT_NA: ""
}

all_pkg_statuses = {
    VERSION_OK: "ok",
    VERSION_UP: "upgraded",
    VERSION_DOWN: "downgraded",
    VERSION_WARN: "warning",
    VERSION_ERR: "error",
    VERSION_NA: "nostatus"
}

node_status = {
    NODE_UP: "up",
    NODE_DOWN: "down",
    NODE_SKIP: "skip"
}

uknown_code = "unk"

all_roles_map = {
    "apt": "repository",
    "bmk": "validation",
    "cfg": "master",
    "cid": "cicd",
    "cmn": "storage_monitor",
    "cmp": "compute",
    "ctl": "openstack_controller",
    "dbs": "database",
    "gtw": "openstack_gateway",
    "kvm": "foundation",
    "log": "stacklight_logger",
    "mon": "monitoring",
    "msg": "messaging",
    "mtr": "stacklight_metering",
    "ntw": "contrail_networking",
    "nal": "contrail_analytics",
    "osd": "storage_node",
    "prx": "proxy",
    "rgw": "storage_rados",
    "unk": "uknown"
}

ubuntu_releases = ["trusty", "xenial", "ubuntu", "bionic"]
all_arch = ["amd64"]
repo_types = {
    "main": "Officially supported software",
    "restricted": "Supported software that is not "
                  "available under a completely free license",
    "universe": "Community maintained software, "
                "i.e. not officially supported software",
    "multiverse": "Software that is not free",
    "contrib": "Free software, but is dependent to non-free software",
    "uknown": "No specific description available"
}

_repos_info_archive = "repo.info.tgz"
_repos_versions_archive = "repo.versions.tgz"
_pkg_desc_archive = "pkg.descriptions.tgz"

_repos_index_filename = "repoindex.json"
_mainteiners_index_filename = "mainteiners.json"
_mirantis_versions_filename = "mirantis_v.json"
_other_versions_filename = "other_v.json"
