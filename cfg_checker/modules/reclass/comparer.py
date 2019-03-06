"""Model Comparer:
- yaml parser
- class tree comparison
"""
import itertools
import os
import yaml

from cfg_checker.reports import reporter
from cfg_checker.common import logger, logger_cli


def get_element(element_path, input_data):     
    paths = element_path.split(":")
    data = input_data
    for i in range(0, len(paths)):
        data = data[paths[i]]
    return data


def pop_element(element_path, input_data):     
    paths = element_path.split(":")
    data = input_data
    # Search for last dict
    for i in range(0, len(paths)-1):
        data = data[paths[i]]
    # pop the actual element
    return data.pop(paths[-1])


class ModelComparer(object):
    """Collection of functions to compare model data.
    """
    # key order is important
    _model_parts = {
        "01_nodes": "nodes",
        "02_system": "classes:system",
        "03_cluster": "classes:cluster",
        "04_other": "classes"
    }
    
    models = {}
    models_path = "/srv/salt/reclass"
    model_name_1 = "source"
    model_path_1 = os.path.join(models_path, model_name_1)
    model_name_2 = "target"
    model_path_2 = os.path.join(models_path, model_name_1)

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
            _folders_list = path[start:].split(os.sep)
            if any(item.startswith(".") for item in _folders_list):
                continue
            # cut absolute part of the path and split folder names
            folders = path[start:].split(os.sep)
            subdir = {}
            # create generator of files that are not hidden
            _exts = ('.yml', '.yaml')
            _subfiles = (_fl for _fl in files
                         if _fl.endswith(_exts) and not _fl.startswith('.'))
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
        
        self.models[name] = {}
        # Brake in according to pathes
        _parts = self._model_parts.keys()
        _parts = sorted(_parts)
        for ii in range(0, len(_parts)):
            self.models[name][_parts[ii]] = pop_element(
                self._model_parts[_parts[ii]],
                raw_tree[root_key]
            )
        
        # save it as a single data object
        self.models[name]["all_diffs"] = raw_tree[root_key]
        return True

    def find_changes(self, dict1, dict2, path=""):
        _report = {}
        for k in dict1.keys():
            # yamls might load values as non-str types
            if not isinstance(k, str):
                _new_path = path + ":" + str(k)
            else:
                _new_path = path + ":" + k
            # ignore _source key
            if k == "_source":
                continue
            # check if this is an env name cluster entry
            if dict2 is not None and \
                    k == self.model_name_1 and \
                    self.model_name_2 in dict2.keys():
                k1 = self.model_name_1
                k2 = self.model_name_2
                if type(dict1[k1]) is dict:
                    if path == "":
                        _new_path = k1
                    _child_report = self.find_changes(
                        dict1[k1],
                        dict2[k2],
                        _new_path
                    )
                    _report.update(_child_report)
            elif dict2 is None or k not in dict2:
                # no key in dict2
                _report[_new_path] = {
                    "type": "value",
                    "raw_values": [dict1[k], "N/A"],
                    "str_values": [
                        "{}".format(dict1[k]),
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
                    _child_report = self.find_changes(
                        dict1[k],
                        dict2[k],
                        _new_path
                    )
                    _report.update(_child_report)
                elif type(dict1[k]) is list and type(dict2[k]) is list:
                    # use ifilterfalse to compare lists of dicts
                    try:
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
                    except TypeError as e:
                        # debug routine,
                        # should not happen, due to list check above
                        logger.error(
                            "Caught lambda type mismatch: {}".format(
                                e.message
                            )
                        )
                        logger_cli.warning(
                            "Types mismatch for correct compare: "
                            "{}, {}".format(
                                type(dict1[k]),
                                type(dict2[k])
                            )
                        )
                        _removed = None
                        _added = None
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
                    # in case of type mismatch
                    # considering it as not equal
                    d1 = dict1
                    d2 = dict2
                    val1 = d1[k] if isinstance(d1, dict) else d1
                    val2 = d2[k] if isinstance(d2, dict) else d2
                    try:
                        match = val1 == val2
                    except TypeError as e:
                        logger.warning(
                            "One of the values is not a dict: "
                            "{}, {}".format(
                                str(dict1),
                                str(dict2)
                            ))
                        match = False
                    if not match:
                        _report[_new_path] = {
                            "type": "value",
                            "raw_values": [val1, val2],
                            "str_values": [
                                "{}".format(val1),
                                "{}".format(val2)
                            ]
                        }
                        logger.info("{}: {}, {}".format(
                            _new_path,
                            val1,
                            val2
                        ))
        return _report


    def generate_model_report_tree(self):
        """Use two loaded models to generate comparison table with
        values are groupped by YAML files
        """
        # We are to cut both models into logical pieces
        # nodes, will not be equal most of the time
        # system, must be pretty much the same or we in trouble
        # cluster, will be the most curious part for comparison
        # other, all of the rest

        _diff_report = {}
        for _key in self._model_parts.keys():
            # tmp report for keys
            _tmp_diffs = self.find_changes(
                self.models[self.model_name_1][_key],
                self.models[self.model_name_2][_key]
            )
            # prettify the report
            for key in _tmp_diffs.keys():
                # break the key in two parts
                _ext = ".yml"
                if ".yaml" in key:
                    _ext = ".yaml"
                _split = key.split(_ext)
                _file_path = _split[0]
                _param_path = "none"
                if len(_split) > 1:
                    _param_path = _split[1]
                _tmp_diffs[key].update({
                    "class_file": _file_path + _ext,
                    "param": _param_path,
                })
            _diff_report[_key[3:]] = {
                "path": self._model_parts[_key],
                "diffs": _tmp_diffs
            }

        _diff_report["diff_names"] = [self.model_name_1, self.model_name_2]
        return _diff_report

    def compare_models(self):
        # Do actual compare using model names from the class
        self.load_model_tree(
            self.model_name_1,
            self.model_path_1
        )
        self.load_model_tree(
            self.model_name_2,
            self.model_path_2
        )
        # Models should have similar structure to be compared
        # classes/system
        # classes/cluster
        # nodes

        diffs = self.generate_model_report_tree()

        report_file = \
            self.model_name_1 + "-vs-" + self.model_name_2 + ".html"
        # HTML report class is post-callable
        report = reporter.ReportToFile(
            reporter.HTMLModelCompare(),
            report_file
        )
        logger_cli.info("...generating report to {}".format(report_file))
        # report will have tabs for each of the comparable entities in diffs
        report({
            "nodes": {},
            "all_diffs": diffs,
        })
        # with open("./gen_tree.json", "w+") as _out:
        #     _out.write(json.dumps(mComparer.generate_model_report_tree))

        return
