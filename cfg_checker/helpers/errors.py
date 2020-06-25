import os
from configparser import NoSectionError

from cfg_checker.common import file_utils as fu
from cfg_checker.common import logger, logger_cli
from cfg_checker.common.config_file import ConfigFile
from cfg_checker.common.exception import ErrorMappingException
from cfg_checker.common.settings import pkg_dir


class ErrorIndex(object):
    # logs folder filenames
    _error_logs_folder_name = ".cfgerrors"
    _conf_filename = "conf"
    # config file object
    conf = None
    # iteration counter
    _iteration = 0
    # local vars for codes
    _area_code = ""
    _delimiter = ""
    _index = 0
    _errors = {}
    _types = {
        0: "Unknown error"
    }

    def __init__(self, area_code, delimiter='-', folder=None):
        self._area_code = area_code
        self._delimiter = delimiter
        self._index += 1

        # save folder
        if folder:
            self._error_logs_folder_name = folder

        # init the error log storage folder
        _folder = os.path.join(pkg_dir, self._error_logs_folder_name)
        self._conf_filename = os.path.join(
            _folder,
            self._conf_filename
        )

        logger_cli.debug(fu.ensure_folder_exists(_folder))
        if not os.path.exists(self._conf_filename):
            # put file with init values
            self.conf = ConfigFile(self._area_code.lower())
            self.conf.set_value('iteration', self._iteration)
            self.conf.save_config(filepath=self._conf_filename)
            logger_cli.debug(
                "... create new config file '{}'".format(
                    self._conf_filename
                )
            )
        else:
            # it exists, try to load latest run
            self.conf = ConfigFile(
                self._area_code.lower(),
                filepath=self._conf_filename
            )
            # check if there is any values there
            try:
                self._iteration = self.conf.get_value(
                    'iteration',
                    value_type=int
                )
                self._iteration += 1
            except NoSectionError:
                self._iteration += 1
                self.conf.set_value('iteration', self._iteration)
                self.conf.save_config(filepath=self._conf_filename)
                logger_cli.debug("... updated config file")

        logger_cli.debug(" ... starting iteration {}".format(self._iteration))

    def save_iteration_data(self):
        # save error log
        _filename = "-".join([self._area_code.lower(), "errors"])
        _filename += "." + str(self._iteration)
        _log_filename = os.path.join(
            pkg_dir,
            self._error_logs_folder_name,
            _filename
        )
        fu.write_lines_to_file(_log_filename, self.get_errors(as_list=True))
        fu.append_line_to_file(_log_filename, "")
        fu.append_lines_to_file(_log_filename, self.get_summary(as_list=True))
        logger_cli.debug("... saved errors to '{}'".format(_log_filename))

        # save last iteration number
        self.conf.set_value('iteration', self._iteration)
        self.conf.save_config()

    def _format_error_code(self, index):
        _t = "{:02d}".format(self._errors[index]['type'])
        _i = "{:04d}".format(index)
        _fmt = self._delimiter.join([self._area_code, _t, _i])
        return _fmt

    def _format_error(self, index):
        # error code
        _code = self._format_error_code(index)
        # prepare data as string list
        _d = self._errors[index]['data']
        _data = ["    {}: {}".format(_k, _v) for _k, _v in _d.items()]
        # format message
        _msg = "### {}:\n    Description: {}\n{}".format(
            _code,
            self.get_error_type_text(self._errors[index]['type']),
            "\n".join(_data)
        )
        return _msg

    def get_error_type_text(self, err_type):
        if err_type not in self._types:
            raise ErrorMappingException(
                "type code {} not found".format(err_type)
            )
        else:
            return self._types[err_type]

    def get_error_code(self, index):
        if index in self._errors.keys():
            return self._format_error(index)
        else:
            raise ErrorMappingException(
                "no error found for index {}".format(index)
            )

    def add_error_type(self, err_type, message):
        if err_type in self._types:
            raise ErrorMappingException(
                "type code {} reserved for {}".format(
                    err_type,
                    self._types[err_type]
                )
            )
        else:
            self._types[err_type] = message

    def add_error(self, err_type, **kwargs):
        # check error type
        if err_type not in self._types.keys():
            logger.error(
                "Error type not listed: '{}'; unknown used".format(err_type)
            )
            err_type = 0
        _err = {
            "type": err_type,
            "data": kwargs
        }
        self._errors[self._index] = _err
        self._index += 1

    def get_errors_total(self):
        return self._index-1

    def get_indices(self):
        return self._errors.keys()

    def get_error(self, index):
        if index in self._errors.keys():
            return self._format_error(index)
        else:
            return "Unknown error index of {}".format(index)

    def get_summary(self, print_zeros=True, as_list=False):
        # create summary with counts per error type
        _list = "\n{:=^8s}\n{:^8s}\n{:=^8s}".format(
            "=",
            "Totals",
            "="
        ).splitlines()

        for _type in self._types.keys():
            _len = len(
                list(
                    filter(
                        lambda i: self._errors[i]['type'] == _type,
                        self._errors
                    )
                )
            )
            if _len:
                _num_str = "{:5d}".format(_len)
            elif print_zeros:
                _num_str = "{:>5s}".format("-")
            else:
                continue
            _list.append(
                "{}: {}".format(
                    _num_str,
                    self._types[_type]
                )
            )

        _total_errors = self.get_errors_total()

        _list.append('-'*20)
        _list.append("{:5d} total events found\n".format(_total_errors))
        if as_list:
            return _list
        else:
            return "\n".join(_list)

    def get_errors(self, as_list=False):
        _list = ["# Events"]
        # Detailed errors
        if self.get_errors_total() > 0:
            # create list of strings with error messages
            for _idx in range(1, self._index):
                _list.append(self._format_error(_idx))
                _list.append("\n")
        else:
            _list.append("-> No events saved")

        if as_list:
            return _list
        else:
            return "\n".join(_list)
