import abc
import jinja2
import os
import six
import time

from cfg_checker.common import const
from cfg_checker.common import logger, logger_cli
from cfg_checker.helpers.console_utils import Progress

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.join(pkg_dir, os.pardir, os.pardir)
pkg_dir = os.path.normpath(pkg_dir)


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
                td[k]['desc']['component'],
                td[k]['desc']['app'],
                k
            )
        )


def get_max(_list):
    return sorted(_list)[-1]


def make_action_label(act):
    _act_labels = {
        const.ACT_UPGRADE: "Upgrade possible",
        const.ACT_NEED_UP: "Needs upgrade",
        const.ACT_NEED_DOWN: "Needs downgrade",
        const.ACT_REPO: "Needs repo update",
        const.ACT_NA: ""
    }
    return _act_labels[act]


def make_action_class(act):
    _act_classes = {
        const.ACT_UPGRADE: "possible",
        const.ACT_NEED_UP: "needs_up",
        const.ACT_NEED_DOWN: "needs_down",
        const.ACT_REPO: "needs_repo",
        const.ACT_NA: ""
    }
    return _act_classes[act]


def make_status_label(sts):
    _status_labels = {
        const.VERSION_OK: "OK",
        const.VERSION_UP: "Upgraded",
        const.VERSION_DOWN: "Downgraded",
        const.VERSION_ERR: "ERROR",
        const.VERSION_NA: "N/A"
    }
    return _status_labels[sts]


def make_status_class(sts):
    return const.all_statuses[sts]


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
        self.jinja2_env.filters['make_status_label'] = make_status_label
        self.jinja2_env.filters['make_status_class'] = make_status_class
        self.jinja2_env.filters['make_action_label'] = make_action_label
        self.jinja2_env.filters['make_action_class'] = make_action_class

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
        data["names"] = data["rc_diffs"].pop("diff_names")
        data["tabs"] = data.pop("rc_diffs")
        
        # counters - mdl_diff
        for _tab in data["tabs"].keys():
            data['counters'][_tab] = len(data["tabs"][_tab]["diffs"].keys())


class HTMLNetworkReport(_TMPLBase):
    tmpl = "network_check_tmpl.j2"


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
