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
                e.message + e.strerror
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
            _exts = ('.yml', '.yaml')
            _subfiles = (file for file in files
                         if file.endswith(_exts) and not file.startswith('.'))
            for _file in _subfiles:
                # cut file extension. All reclass files are '.yml'
                _subnode = _file
                # load all YAML class data into the tree
                subdir[_subnode] = self.load_yaml_class(
                    os.path.join(path, _file)
                )
                try:
                    # Save original filepath, just in case
                    subdir[_subnode]["_source"] = os.path.join(
                        path[start:],
                        _file
                    )
                except Exception:
                    logger.warning(
                        "Non-yaml file detected: {}".format(_file)
                    )
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
                if dict2 is None or k not in dict2:
                    # no key in dict2
                    _report[_new_path] = {
                        "type": "value",
                        "raw_values": [dict1[k], "N/A"],
                        "str_values": [
                            "{}".format(dict1[k]),
                            "n/a"
                        ],
                        "str_short": [
                            "{:25.25}...".format(str(dict1[k])),
                            "n/a"
                        ]
                    }
                    logger.info(
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
                        _original = ["= {}".format(item) for item in dict1[k]]
                        if _removed or _added:
                            _removed_str_lst = ["- {}".format(item)
                                                for item in _removed]
                            _added_str_lst = ["+ {}".format(item)
                                              for item in _added]
                            _report[_new_path] = {
                                "type": "list",
                                "raw_values": [
                                    dict1[k],
                                    _removed_str_lst + _added_str_lst
                                ],
                                "str_values": [
                                    "{}".format('\n'.join(_original)),
                                    "{}\n{}".format(
                                        '\n'.join(_removed_str_lst),
                                        '\n'.join(_added_str_lst)
                                    )
                                ],
                                "str_short": [
                                    "{} items".format(len(dict1[k])),
                                    "{}\n{}".format(
                                        '\n'.join(_removed_str_lst),
                                        '\n'.join(_added_str_lst)
                                    )
                                ]
                            }
                            logger.info(
                                "{}:\n"
                                "{} original items total".format(
                                    _new_path,
                                    len(dict1[k])
                                )
                            )
                            if _removed:
                                logger.info(
                                    "{}".format('\n'.join(_removed_str_lst))
                                )
                            if _added:
                                logger.info(
                                    "{}".format('\n'.join(_added_str_lst))
                                )
                    else:
                        if dict1[k] != dict2[k]:
                            _str1 = str(dict1[k])
                            _str1_cut = "{:20.20}...".format(str(dict1[k]))
                            _str2 = str(dict2[k])
                            _str2_cut = "{:20.20}...".format(str(dict2[k]))
                            _report[_new_path] = {
                                "type": "value",
                                "raw_values": [dict1[k], dict2[k]],
                                "str_values": [
                                    "{}".format(dict1[k]),
                                    "{}".format(dict2[k])
                                ],
                                "str_short": [
                                    _str1 if len(_str1) < 20 else _str1_cut,
                                    _str2 if len(_str1) < 20 else _str2_cut,
                                ]
                            }
                            logger.info("{}: {}, {}".format(
                                _new_path,
                                dict1[k],
                                dict2[k]
                            ))
            return _report
        # tmp report for keys
        diff_report = find_changes(
            self.models["inspur_Aug"],
            self.models["inspur_Original"]
        )
        # prettify the report
        for key in diff_report.keys():
            # break the key in two parts
            _ext = ".yml"
            if ".yaml" in key:
                _ext = ".yaml"
            _split = key.split(_ext)
            _file_path = _split[0]
            _param_path = "none"
            if len(_split) > 1:
                _param_path = _split[1]
            diff_report[key].update({
                "class_file": _file_path + _ext,
                "param": _param_path,
            })

        diff_report["diff_names"] = ["inspur_Aug", "inspur_Original"]
        return diff_report


# temporary executing the parser as a main prog
if __name__ == '__main__':
    mComparer = ModelComparer()
    mComparer.load_model_tree(
        'inspur_Aug',
        '/Users/savex/proj/inspur_hc/reclass_cmp/reclass-20180810'
    )
    mComparer.load_model_tree(
        'inspur_Original',
        '/Users/savex/proj/inspur_hc/reclass_cmp/reclass_original'
    )
    diffs = mComparer.generate_model_report_tree()

    report_file = "./mdl_diff_original.html"
    report = reporter.ReportToFile(
        reporter.HTMLModelCompare(),
        report_file
    )
    logger_cli.info("...generating report to {}".format(report_file))
    report({
        "nodes": {},
        "diffs": diffs
    })
    # with open("./gen_tree.json", "w+") as _out:
    #     _out.write(json.dumps(mComparer.generate_model_report_tree))
