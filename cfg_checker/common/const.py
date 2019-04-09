"""Constants that is not to be changed and used in all other files
"""

from __future__ import print_function, absolute_import

import itertools

_cnt = itertools.count()
NODE_DOWN = next(_cnt)
NODE_UP = next(_cnt)

# version const order is important!
# biggest get shown in report top row
VERSION_NA = next(_cnt)
VERSION_OK = next(_cnt)
VERSION_UP = next(_cnt)
VERSION_DOWN = next(_cnt)
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
    ACT_REPO: "needs repo update",
    ACT_NA: ""
}

all_statuses = {
    VERSION_OK: "ok",
    VERSION_UP: "upgraded",
    VERSION_DOWN: "downgraded",
    VERSION_ERR: "error",
    VERSION_NA: "no status"
}

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
    "osd": "storage_node",
    "prx": "proxy",
    "rgw": "storage_rados"
}
