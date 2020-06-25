import abc
import os
import re
import time

from cfg_checker.common import const
from cfg_checker.common import logger_cli
from cfg_checker.common.file_utils import read_file_as_lines
from cfg_checker.nodes import salt_master

import jinja2

import six

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.join(pkg_dir, os.pardir, os.pardir)
pkg_dir = os.path.normpath(pkg_dir)

# % threshhold values
_disk_warn = 80
_disk_critical = 90
_ram_warn = 5
_ram_critical = 3
_softnet_interval = 5

UP = const.NODE_UP
DOWN = const.NODE_DOWN
SKIP = const.NODE_SKIP


def line_breaks(text):
    # replace python linebreaks with html breaks
    return text.replace("\n", "<br />")


def get_sorted_keys(td):
    # detect if we can sort by desc
    # Yes, this is slow, but bullet-proof from empty desc
    _desc = all([bool(td[k]['desc']) for k in td.keys()])
    # Get sorted list
    if not _desc:
        return sorted(td.keys())
    else:
        return sorted(
            td.keys(),
            key=lambda k: (
                td[k]['desc']['section'],
                td[k]['desc']['app'],
                k
            )
        )


def get_max(_list):
    return sorted(_list)[-1]


def make_pkg_action_label(act):
    _act_labels = {
        const.ACT_UPGRADE: "Upgrade possible",
        const.ACT_NEED_UP: "Needs upgrade",
        const.ACT_NEED_DOWN: "Needs downgrade",
        const.ACT_REPO: "Repo update",
        const.ACT_NA: ""
    }
    return _act_labels[act]


def make_pkg_action_class(act):
    _act_classes = {
        const.ACT_UPGRADE: "possible",
        const.ACT_NEED_UP: "needs_up",
        const.ACT_NEED_DOWN: "needs_down",
        const.ACT_REPO: "needs_repo",
        const.ACT_NA: ""
    }
    return _act_classes[act]


def make_pkg_status_label(sts):
    _status_labels = {
        const.VERSION_OK: "OK",
        const.VERSION_UP: "Upgraded",
        const.VERSION_DOWN: "Downgraded",
        const.VERSION_WARN: "WARNING",
        const.VERSION_ERR: "ERROR",
        const.VERSION_NA: "N/A"
    }
    return _status_labels[sts]


def make_pkg_status_class(sts):
    return const.all_pkg_statuses[sts]


def make_node_status(sts):
    return const.node_status[sts]


def make_repo_info(repos):
    _text = ""
    for r in repos:
        # tag
        _text += r['tag'] + ": "
        # repo header
        _text += " ".join([
            r['subset'],
            r['release'],
            r['ubuntu-release'],
            r['type'],
            r['arch']
        ]) + ", "
        # maintainer w/o email
        _text += ascii(r['maintainer'][:r['maintainer'].find('<')-1])
        # newline
        _text += "<br />"
    return _text


@six.add_metaclass(abc.ABCMeta)
class _Base(object):
    def __init__(self):
        self.jinja2_env = self.init_jinja2_env()

    @abc.abstractmethod
    def __call__(self, payload):
        pass

    @staticmethod
    def init_jinja2_env():
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.join(pkg_dir, 'templates')),
            trim_blocks=True,
            lstrip_blocks=True)


class _TMPLBase(_Base):
    @abc.abstractproperty
    def tmpl(self):
        pass

    @staticmethod
    def _count_totals(data):
        data['counters']['total_nodes'] = len(data['nodes'])

    def __call__(self, payload):
        # init data structures
        data = self.common_data()
        # payload should have pre-sorted structure according to report called
        # nodes, openstack_release, mcp_release, etc...
        data.update(payload)

        # add template specific data
        self._extend_data(data)

        # do counts global
        self._count_totals(data)

        # specific filters
        self.jinja2_env.filters['linebreaks'] = line_breaks
        self.jinja2_env.filters['get_max'] = get_max

        self.jinja2_env.filters['get_sorted_keys'] = get_sorted_keys
        self.jinja2_env.filters['pkg_status_label'] = make_pkg_status_label
        self.jinja2_env.filters['pkg_status_class'] = make_pkg_status_class
        self.jinja2_env.filters['pkg_action_label'] = make_pkg_action_label
        self.jinja2_env.filters['pkg_action_class'] = make_pkg_action_class
        self.jinja2_env.filters['node_status_class'] = make_node_status
        self.jinja2_env.filters['pkg_repo_info'] = make_repo_info

        # render!
        logger_cli.info("-> Using template: {}".format(self.tmpl))
        tmpl = self.jinja2_env.get_template(self.tmpl)
        logger_cli.info("-> Rendering")
        return tmpl.render(data)

    def common_data(self):
        return {
            'counters': {},
            'salt_info': {},
            'gen_date': time.strftime("%m/%d/%Y %H:%M:%S")
        }

    def _extend_data(self, data):
        pass


# HTML Package versions report
class CSVAllPackages(_TMPLBase):
    tmpl = "pkg_versions_csv.j2"


# HTML Package versions report
class HTMLPackageCandidates(_TMPLBase):
    tmpl = "pkg_versions_html.j2"


# Package versions report
class HTMLModelCompare(_TMPLBase):
    tmpl = "model_tree_cmp_tmpl.j2"

    def _extend_data(self, data):
        # move names into separate place
        data["names"] = data["diffs"].pop("diff_names")
        data["tabs"] = data.pop("diffs")

        # counters - mdl_diff
        for _tab in data["tabs"].keys():
            data['counters'][_tab] = len(data["tabs"][_tab]["diffs"].keys())


class HTMLNetworkReport(_TMPLBase):
    tmpl = "network_check_tmpl.j2"

    def _extend_data(self, data):
        def get_bytes(value):
            _char = value[-1]
            _ord = ord(_char)
            if _ord > 47 and _ord < 58:
                # bytes comes with no Char
                return int(value)
            else:
                _sizes = ["*", "K", "M", "G", "T"]
                _flo = float(value[:-1])
                _pwr = 1
                if _char in _sizes:
                    _pwr = _sizes.index(_char)
                return int(_flo**_pwr)

        def _dmidecode(_dict, type=0):
            # _key = "dmi"
            _key_r = "dmi_r"
            _f_cmd = salt_master.get_cmd_for_nodes
            _cmd = "dmidecode -t {}".format(type)
            _f_cmd(_cmd, _key_r, target_dict=_dict)
            # TODO: parse BIOS output or given type
            pass

        def _lsblk(_dict):
            # _key = "lsblk"
            _key_r = "lsblk_raw"
            _f_cmd = salt_master.get_cmd_for_nodes
            _columns = [
                "NAME",
                "HCTL",
                "TYPE",
                "SIZE",
                "VENDOR",
                "MODEL",
                "SERIAL",
                "REV",
                "TRAN"
            ]
            _cmd = "lsblk -S --output {}".format(",".join(_columns))
            _f_cmd(_cmd, _key_r, target_dict=_dict)
            # TODO: parse lsblk output
            pass

        def _lscpu(_dict):
            _key = "lscpu"
            _key_r = "lscpu_raw"
            # get all of the values
            _f_cmd = salt_master.get_cmd_for_nodes
            _cmd = "lscpu | sed -n '/\\:/s/ \\+/ /gp'"
            _f_cmd(_cmd, _key_r, target_dict=_dict)
            # parse them and put into dict
            for node, dt in _dict.items():
                dt[_key] = {}
                if dt['status'] == DOWN or dt['status'] == SKIP:
                    continue
                if not dt[_key_r]:
                    # no stats collected, put negatives
                    dt.pop(_key_r)
                    continue
                lines = dt[_key_r].splitlines()
                for line in lines:
                    li = line.split(':')
                    _var_name = li[0].lower()
                    _var_name = re.sub(' ', '_', _var_name)
                    _var_name = re.sub('|'.join(['\\(', '\\)']), '', _var_name)
                    _var_value = li[1].strip()
                    dt[_key][_var_name] = _var_value
                dt.pop(_key_r)
                # detect virtual nodes
                if "hypervisor_vendor" in dt[_key]:
                    dt['node_type'] = "virtual"
                else:
                    dt['node_type'] = "physical"

        def _free(_dict):
            _key = "ram"
            _key_r = "ram_raw"
            _f_cmd = salt_master.get_cmd_for_nodes
            _cmd = "free -h | sed -n '/Mem/s/ \\+/ /gp'"
            _f_cmd(_cmd, _key_r, target_dict=_dict)
            # parse them and put into dict
            for node, dt in _dict.items():
                dt[_key] = {}
                if dt['status'] == DOWN or dt['status'] == SKIP:
                    continue
                if not dt[_key_r]:
                    # no stats collected, put negatives
                    dt.pop(_key_r)
                    continue
                li = dt[_key_r].split()
                dt[_key]['total'] = li[1]
                dt[_key]['used'] = li[2]
                dt[_key]['free'] = li[3]
                dt[_key]['shared'] = li[4]
                dt[_key]['cache'] = li[5]
                dt[_key]['available'] = li[6]

                _total = get_bytes(li[1])
                _avail = get_bytes(li[6])
                _m = _avail * 100.0 / _total
                if _m < _ram_critical:
                    dt[_key]["status"] = "fail"
                elif _m < _ram_warn:
                    dt[_key]["status"] = "warn"
                else:
                    dt[_key]["status"] = ""

        def _services(_dict):
            _key = "services"
            _key_r = "services_raw"
            _f_cmd = salt_master.get_cmd_for_nodes
            _cmd = "service --status-all"
            _f_cmd(_cmd, _key_r, target_dict=_dict)
            for node, dt in _dict.items():
                dt[_key] = {}
                if dt['status'] == DOWN or dt['status'] == SKIP:
                    continue
                if not dt[_key_r]:
                    # no stats collected, put negatives
                    dt.pop(_key_r)
                    continue
                lines = dt[_key_r].splitlines()
                for line in lines:
                    li = line.split()
                    _status = li[1]
                    _name = li[3]
                    if _status == '-':
                        dt[_key][_name] = False
                    elif _status == '+':
                        dt[_key][_name] = True
                    else:
                        dt[_key][_name] = None
                dt.pop(_key_r)

        def _vcp_status(_dict):
            _key = "virsh"
            _key_r = "virsh_raw"
            salt_master.get_cmd_for_nodes(
                "virsh list --all | sed -n -e '/[0-9]/s/ \\+/ /gp'",
                _key_r,
                target_dict=_dict,
                nodes="kvm*"
            )
            _kvm = filter(lambda x: x.find("kvm") >= 0, _dict.keys())
            for node in _kvm:
                dt = _dict[node]
                dt[_key] = {}
                if dt['status'] == DOWN or dt['status'] == SKIP:
                    continue
                if not dt[_key_r]:
                    # no stats collected, put negatives
                    dt.pop(_key_r)
                    continue
                lines = dt[_key_r].splitlines()
                for line in lines:
                    li = line.split()
                    _id = li[0]
                    _name = li[1]
                    _status = li[2]
                    dt[_key][_name] = {
                        'id': _id,
                        'status': _status
                    }
                dt.pop(_key_r)

        # query per-cpu and count totals
        # total (0), dropped(1), squeezed (2), collision (7)
        def _soft_net_stats(_dict):
            _key = "net_stats"
            _key_r = "net_stats_raw"
            _f_cmd = salt_master.get_cmd_for_nodes
            _cmd = "cat /proc/net/softnet_stat; echo \\#; " \
                "sleep {}; cat /proc/net/softnet_stat".format(
                    _softnet_interval
                )
            _f_cmd(_cmd, _key_r, target_dict=_dict)
            for node, dt in _dict.items():
                _cpuindex = 1
                _add_mode = True
                # totals for start mark
                _ts = [0, 0, 0, 0]
                # skip if node is down
                if dt['status'] == DOWN or dt['status'] == SKIP:
                    dt[_key] = {
                        "total": [-1, -1, -1, -1]
                    }
                    continue
                if not dt[_key_r]:
                    # no stats collected, put negatives
                    dt.pop(_key_r)
                    dt[_key] = {
                        "total": [-1, -1, -1, -1]
                    }
                    continue
                # final totals
                dt[_key] = {
                    "total": [0, 0, 0, 0]
                }
                lines = dt[_key_r].splitlines()
                for line in lines:
                    if line.startswith("#"):
                        _add_mode = False
                        _cpuindex = 1
                        continue
                    li = line.split()
                    _c = [
                        int(li[0], 16),
                        int(li[1], 16),
                        int(li[2], 16),
                        int(li[7], 16)
                    ]
                    _id = "cpu{:02}".format(_cpuindex)
                    if _id not in dt[_key]:
                        dt[_key][_id] = []
                    _dc = dt[_key][_id]
                    if _add_mode:
                        # saving values and adding totals
                        dt[_key][_id] = _c
                        # save start totals
                        _ts = [_ts[i]+_c[i] for i in range(0, len(_c))]
                    else:
                        # this is second measurement
                        # subtract all values
                        for i in range(len(_c)):
                            dt[_key][_id][i] = _c[i] - _dc[i]
                            dt[_key]["total"][i] += _c[i]
                    _cpuindex += 1
                # finally, subtract initial totals
                for k, v in dt[_key].items():
                    if k != "total":
                        dt[_key][k] = [v[i] / 5. for i in range(len(v))]
                    else:
                        dt[_key][k] = [(v[i]-_ts[i])/5. for i in range(len(v))]
                dt.pop(_key_r)

        # prepare yellow and red marker values
        data["const"] = {
            "net_interval": _softnet_interval,
            "ram_warn": _ram_warn,
            "ram_critical": _ram_critical,
            "disk_warn": _disk_warn,
            "disk_critical": _disk_critical,
            "services": read_file_as_lines(
                            os.path.join(
                                pkg_dir,
                                'etc',
                                'services.list'
                            )
                        )
        }

        # get kernel version
        salt_master.get_cmd_for_nodes(
            "uname -r",
            "kernel",
            target_dict=data["nodes"]
        )
        # process lscpu data
        _lscpu(data["nodes"])

        # free ram
        # sample: 16425392 14883144 220196
        _free(data["nodes"])

        # disk space
        # sample: /dev/vda1 78G 33G 45G 43%
        _key = "disk"
        _key_r = "disk_raw"
        salt_master.get_cmd_for_nodes(
            "df -h | sed -n '/^\\/dev/s/ \\+/ /gp' | cut -d\" \" -f 1-5",
            "disk_raw",
            target_dict=data["nodes"]
        )
        for dt in data["nodes"].values():
            dt["disk"] = {}
            dt["disk_max_dev"] = None
            if dt['status'] == DOWN:
                dt["disk"]["unknown"] = {}
                dt["disk_max_dev"] = "unknown"
                continue
            if dt['status'] == SKIP:
                dt["disk"]["skipped"] = {}
                dt["disk_max_dev"] = "skipped"
                continue
            if not dt[_key_r]:
                # no stats collected, put negatives
                dt.pop(_key_r)
                dt[_key] = {}
                continue
            # show first device row by default
            _d = dt["disk"]
            _r = dt["disk_raw"]
            _r = _r.splitlines()
            _max = -1
            for idx in range(0, len(_r)):
                _t = _r[idx].split()
                _d[_t[0]] = {}
                _d[_t[0]]['v'] = _t[1:]
                _chk = int(_t[-1].split('%')[0])
                if _chk > _max:
                    dt["disk_max_dev"] = _t[0]
                    _max = _chk
                if _chk > _disk_critical:
                    _d[_t[0]]['f'] = "fail"
                elif _chk > _disk_warn:
                    _d[_t[0]]['f'] = "warn"
                else:
                    _d[_t[0]]['f'] = ""

        # prepare networks data for report
        for net, net_v in data['map'].items():
            for node, ifs in net_v.items():
                for d in ifs:
                    _err = "fail"
                    d['interface_error'] = _err if d['interface_error'] else ""
                    d['mtu_error'] = _err if d['mtu_error'] else ""
                    d['status_error'] = _err if d['status_error'] else ""
                    d['subnet_gateway_error'] = \
                        _err if d['subnet_gateway_error'] else ""

        _services(data["nodes"])
        # vcp status
        # query virsh and prepare for report
        _vcp_status(data["nodes"])

        # soft net stats
        _soft_net_stats(data["nodes"])


class ReportToFile(object):
    def __init__(self, report, target):
        self.report = report
        self.target = target

    def __call__(self, payload):
        payload = self.report(payload)

        if isinstance(self.target, six.string_types):
            self._wrapped_dump(payload)
        else:
            self._dump(payload, self.target)

    def _wrapped_dump(self, payload):
        with open(self.target, 'wt') as target:
            self._dump(payload, target)

    @staticmethod
    def _dump(payload, target):
        target.write(payload)
