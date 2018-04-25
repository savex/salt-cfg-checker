import jinja2
import six
import abc
import os

from check_versions.common import const

pkg_dir = os.path.dirname(__file__)
pkg_dir = os.path.join(pkg_dir, os.pardir)
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

    def __call__(self, nodes):
        # init data structures
        data = self.common_data()
        data.update({
            "nodes": nodes
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


# Package versions report
class HTMLPackageVersions(_TMPLBase):
    tmpl = "pkg_versions_tmpl.j2"

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
        _all_pkg = 0
        for key, value in data['nodes'].iteritems():
            # add count of packages for this node to total
            _all_pkg += len(value.keys())

            # count differences
            data['counters'][key] = {}
            data['counters'][key]['packages'] = len(value['packages'].keys())
            data['counters'][key]['package_diff'] = 0
            for pkg_name, pkg_value in value['packages'].iteritems():
                if pkg_value['installed'] != pkg_value['candidate']:
                    pkg_value['is_equal'] = False
                    pkg_value['fail_uniq'] = self.is_fail_uniq(
                        pkg_value,
                        pkg_name,
                        data['nodes'],
                        key
                    )
                    data['counters'][key]['package_diff'] += 1
                else:
                    pkg_value['is_equal'] = True
                    pkg_value['fail_uniq'] = False

        data['counters']['total_packages'] = _all_pkg


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
