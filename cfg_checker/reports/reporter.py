import jinja2
import six
import abc
import os

from cfg_checker.common import const

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.join(pkg_dir, os.pardir, os.pardir)
pkg_dir = os.path.normpath(pkg_dir)


def shortname(node_fqdn):
    # form shortname out of node fqdn
    return node_fqdn.split(".", 1)[0]


def is_equal(pkg_dict):
    # compare versions of given package
    return pkg_dict['installed'] == pkg_dict['candidate']


def is_active(node_dict):
    # check node status in node dict
    return node_dict['status'] == const.NODE_UP


def line_breaks(text):
    # replace python linebreaks with html breaks
    return text.replace("\n", "<br />")


def get_sorted_keys(td):
    return sorted(
        td.keys(),
        key=lambda k: (
            td[k]['desc']['component'],
            td[k]['desc']['app']
        )
    )


def make_action_label(act):
    return const.all_actions[act]


def make_status_label(sts):
    return const.all_statuses[sts]


def make_cmp_label(text):
    _d = {
        const.VERSION_EQUAL: "equal",
        const.VERSION_DIFF: "different",
        const.VERSION_NA: "no status"
    }
    if text in _d:
        return _d[text]
    else:
        return text + '(!)'


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
        # payload should have pre-sorted structure
        # system, nodes, clusters, and the rest in other
        data.update({
            "nodes": payload['nodes'],
            "rc_diffs": payload['rc_diffs'],
            "pkg_diffs": payload['pkg_diffs'],
            "all": payload['all_pkg'],
            "mcp_release": payload['mcp_release'],
            "openstack_release": payload['openstack_release'],
            "tabs": {}
        })

        # add template specific data
        self._extend_data(data)

        # do counts global
        self._count_totals(data)

        # specific filters
        self.jinja2_env.filters['shortname'] = shortname
        self.jinja2_env.filters['is_equal'] = is_equal
        self.jinja2_env.filters['is_active'] = is_active
        self.jinja2_env.filters['linebreaks'] = line_breaks
        self.jinja2_env.filters['make_cmp_label'] = make_cmp_label
        self.jinja2_env.filters['make_status_label'] = make_status_label
        self.jinja2_env.filters['make_action_label'] = make_action_label
        self.jinja2_env.filters['get_sorted_keys'] = get_sorted_keys

        # render!
        tmpl = self.jinja2_env.get_template(self.tmpl)
        return tmpl.render(data)

    def common_data(self):
        return {
            'counters': {},
            'salt_info': {}
        }

    def _extend_data(self, data):
        pass


# HTML Package versions report
class CSVAllPackages(_TMPLBase):
    tmpl = "pkg_versions_csv.j2"


# HTML Package versions report
class HTMLPackageCandidates(_TMPLBase):
    tmpl = "pkg_versions_html.j2"

    @staticmethod
    def is_fail_uniq(p_dict, p_name, nodes, node_name):
        # look up package fail for nodes with similar role
        _tgroup = nodes[node_name]['node_group']
        # filter all nodes with the same role
        _nodes_list = filter(
            lambda nd: nodes[nd]['node_group'] == _tgroup and nd != node_name,
            nodes
        )
        # lookup same package
        _fail_uniq = False
        for _node_name in _nodes_list:
            # check if there is a package present on node
            _nd = nodes[_node_name]['packages']
            if p_name not in _nd:
                continue
            # if both backages has same version and differ from candidate
            if p_dict['candidate'] == _nd[p_name]['candidate'] \
                    and _nd[p_name]['candidate'] == _nd[p_name]['installed']:
                # it is not uniq, mark and break
                _fail_uniq = True
        return _fail_uniq

 
    def _extend_data(self, data):
        # labels
        data['cmp'] = {
            const.VERSION_EQUAL: "equal",
            const.VERSION_DIFF: "different",
            const.VERSION_NA: "n/a"
        }

        # Presort packages
        data['critical'] = {}
        data['system'] = {}
        data['other'] = {}
        data['unlisted'] = {}
        while len(data['all']) > 0:
            _pn, _val = data['all'].popitem()
            if not _val['desc']:
                # not listed package in version lib
                data['unlisted'].update({
                    _pn: _val
                })
            else:
                _c = _val['desc']['component']
                # critical: not blank and not system
                if len(_c) > 0 and _c != 'System':
                    data['critical'].update({
                        _pn: _val
                    })
                # system
                elif _c == 'System':
                    data['system'].update({
                        _pn: _val
                    })
                # rest
                else:
                    data['other'].update({
                        _pn: _val
                    })
        
        # Count values on per-node basis
        for key, value in data['nodes'].iteritems():
            # count differences
            data['counters'][key] = {}
            data['counters'][key]['packages'] = len(value['packages'].keys())
            data['counters'][key]['package_diff'] = 0
            data['counters'][key]['package_eq'] = 0

            # Lookup if this fail is uniq for this node
            for pkg_name, pkg_value in value['packages'].iteritems():
                if pkg_value['is_equal']:
                    pkg_value['fail_uniq'] = False
                    data['counters'][key]['package_eq'] += 1
                else:
                    pkg_value['fail_uniq'] = self.is_fail_uniq(
                        pkg_value,
                        pkg_name,
                        data['nodes'],
                        key
                    )
                    data['counters'][key]['package_diff'] += 1
       
        # Count values on all-diffs basis
        for key, value in data['pkg_diffs'].iteritems():
            data['counters'][key] = {}
            data['counters'][key]['df_nodes'] = len(value['df_nodes'].keys())
            data['counters'][key]['eq_nodes'] = len(value['eq_nodes'])

        # Save all packages counter
        data['counters']['total_packages'] = data['pkg_diffs'].keys()


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
