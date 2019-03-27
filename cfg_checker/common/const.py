"""Constants that is not to be changed and used in all other files
"""

from __future__ import print_function, absolute_import

import itertools

_cnt = itertools.count()
NODE_DOWN = next(_cnt)
NODE_UP = next(_cnt)

VERSION_EQUAL = next(_cnt)
VERSION_DIFF_EPOCH = next(_cnt)
VERSION_DIFF_EPOCH_UPGRADE = next(_cnt)
VERSION_DIFF_EPOCH_DOWNGRADE = next(_cnt)
VERSION_DIFF_MAJOR = next(_cnt)
VERSION_DIFF_MAJOR_UPGRADE = next(_cnt)
VERSION_DIFF_MAJOR_DOWNGRADE = next(_cnt)
VERSION_DIFF_DEBIAN = next(_cnt)

del _cnt

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
