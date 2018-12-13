"""Model Comparer:
- yaml parser
- class tree comparison
"""
import itertools
# import json
import os
import yaml

import reporter
from ci_checker.common import utils
from ci_checker.common import base_config, logger, logger_cli, PKG_DIR


class ModelComparer(object):
    """Collection of functions to compare model data.
    """
    models = {}

    @staticmethod
    def load_yaml_class(fname):
        """Loads a yaml from the file and forms a tree item

        Arguments:
            fname {string} -- full path to the yaml file
        """
        _yaml = {}
        try:
            _size = 0
            with open(fname, 'r') as f:
                _yaml = yaml.load(f)
                _size = f.tell()
            # TODO: do smth with the data
            if not _yaml:
                logger_cli.warning("WARN: empty file '{}'".format(fname))
                _yaml = {}
            else:
                logger.debug("...loaded YAML '{}' ({}b)".format(fname, _size))
            return _yaml
        except yaml.YAMLError as exc:
            logger_cli.error(exc)
        except IOError as e:
            logger_cli.error(
                "Error loading file '{}': {}".format(fname, e.message)
            )
            raise Exception("CRITICAL: Failed to load YAML data: {}".format(
                e.message
            ))

    def load_model_tree(self, name, root_path="/srv/salt/reclass"):
        """Walks supplied path for the YAML filed and loads the tree

        Arguments:
            root_folder_path {string} -- Path to Model's root folder. Optional
        """
        logger_cli.info("Loading reclass tree from '{}'".format(root_path))
        # prepare the file tree to walk
        raw_tree = {}
        # Credits to Andrew Clark@MIT. Original code is here:
        # http://code.activestate.com/recipes/577879-create-a-nested-dictionary-from-oswalk/
        root_path = root_path.rstrip(os.sep)
        start = root_path.rfind(os.sep) + 1
        root_key = root_path.rsplit(os.sep, 1)[1]
        # Look Ma! I am walking the file tree with no recursion!
        for path, dirs, files in os.walk(root_path):
            # if this is a hidden folder, ignore it
            _filders_list = path[start:].split(os.sep)
            if any(item.startswith(".") for item in _filders_list):
                continue
            # cut absolute part of the path and split folder names
            folders = path[start:].split(os.sep)
            subdir = {}
            # create generator of files that are not hidden
            _subfiles = (file for file in files if not file.startswith("."))
            for _file in _subfiles:
                # cut file extension. All reclass files are '.yml'
                _subnode = _file
                # load all YAML class data into the tree
                subdir[_subnode] = self.load_yaml_class(
                    os.path.join(path, _file)
                )
                # Save original filepath, just in case
                subdir[_subnode]["_source"] = os.path.join(path[start:], _file)
            # creating dict structure out of folder list. Pure python magic
            parent = reduce(dict.get, folders[:-1], raw_tree)
            parent[folders[-1]] = subdir
        # save it as a single data object
        self.models[name] = raw_tree[root_key]
        return True

    def generate_model_report_tree(self):
        """Use all loaded models to generate comparison table with
        values are groupped by YAML files
        """
        def find_changes(dict1, dict2, path=""):
            _report = {}
            for k in dict1.keys():
                _new_path = path + ":" + k
                if k == "_source":
                    continue
                if k not in dict2:
                    # no key in dict2
                    _report[_new_path] = [dict1[k], "N/A"]
                    logger_cli.info(
                        "{}: {}, {}".format(_new_path, dict1[k], "N/A")
                    )
                else:
                    if type(dict1[k]) is dict:
                        if path == "":
                            _new_path = k
                        _child_report = find_changes(
                            dict1[k],
                            dict2[k],
                            _new_path
                        )
                        _report.update(_child_report)
                    elif type(dict1[k]) is list:
                        # use ifilterfalse to compare lists of dicts
                        _removed = list(
                            itertools.ifilterfalse(
                                lambda x: x in dict2[k],
                                dict1[k]
                            )
                        )
                        _added = list(
                            itertools.ifilterfalse(
                                lambda x: x in dict1[k],
                                dict2[k]
                            )
                        )
                        if _removed or _added:
                            _removed_str_lst = ["- {}".format(item)
                                                for item in _removed]
                            _added_str_lst = ["+ {}".format(item)
                                              for item in _added]
                            _report[_new_path] = [
                                dict1[k],
                                _removed_str_lst + _added_str_lst
                            ]
                            logger_cli.info(
                                "{}:\n"
                                "{} original items total".format(
                                    _new_path,
                                    len(dict1[k])
                                )
                            )
                            if _removed:
                                logger_cli.info(
                                    "{}".format('\n'.join(_removed_str_lst))
                                )
                            if _added:
                                logger_cli.info(
                                    "{}".format('\n'.join(_added_str_lst))
                                )
                    else:
                        if dict1[k] != dict2[k]:
                            _report[_new_path] = [dict1[k], dict2[k]]
                            logger_cli.info("{}: {}, {}".format(
                                _new_path,
                                dict1[k],
                                dict2[k]
                            ))
            return _report
        # tmp report for keys
        diff_report = find_changes(
            self.models["inspur_Aug"],
            self.models['inspur_Dec']
        )
        return diff_report


# temporary executing the parser as a main prog
if __name__ == '__main__':
    mComparer = ModelComparer()
    mComparer.load_model_tree(
        'inspur_Aug',
        '/Users/savex/proj/inspur_hc/reclass_cmp/reclass-20180810'
    )
    mComparer.load_model_tree(
        'inspur_Dec',
        '/Users/savex/proj/inspur_hc/reclass_cmp/reclass-20181210'
    )
    diffs = mComparer.generate_model_report_tree()

    report = reporter.ReportToFile(
        reporter.HTMLModelCompare(),
        './mdl_diff.html'
    )
    report(mdl_diff=diffs)
    # with open("./gen_tree.json", "w+") as _out:
    #     _out.write(json.dumps(mComparer.generate_model_report_tree))
