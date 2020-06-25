import contextlib
import io
import os
import sys
import unittest
import logging

from copy import deepcopy

tests_dir = os.path.dirname(__file__)
tests_dir = os.path.normpath(tests_dir)
tests_dir = os.path.abspath(tests_dir)


class CfgCheckerTestBase(unittest.TestCase):
    dummy_base_var = 0
    last_stderr = ""
    last_stdout = ""

    def _safe_import(self, _str):
        if "." not in _str:
            return self._safe_import_module(_str)
        else:
            return self._safe_import_class(_str)

    def _safe_import_class(self, _str):
        _import_msg = ""
        attrs = _str.split('.')
        _import_msg, _module = self._safe_import_module(attrs[0])
        if _import_msg:
            return _import_msg, _module
        else:
            for attr_name in attrs[1:]:
                _module = getattr(_module, attr_name)
            return "", _module

    @staticmethod
    def _safe_import_module(_str, *args, **kwargs):
        _import_msg = ""
        _module = None

        try:
            _module = __import__(_str, *args, **kwargs)
        except ImportError as e:
            _import_msg = e.message

        return _import_msg, _module

    @staticmethod
    def _safe_run(_obj, *args, **kwargs):
        _m = ""
        try:
            _r = _obj(*args, **kwargs)
        except Exception as ex:
            if hasattr(ex, 'message'):
                _m = "{}: {}".format(str(_obj), ex.message)
            elif hasattr(ex, 'msg'):
                _m = "{}: {}".format(str(_obj), ex.msg)
            else:
                _m = "{}: {}".format(str(_obj), "<no message>")
        return _r, _m

    def run_main(self, args_list):
        _module_name = 'cfg_checker.cfg_check'
        _m = self._try_import(_module_name)
        with self.save_arguments():
            with self.redirect_output():
                with self.assertRaises(SystemExit) as ep:
                    sys.argv = ["fake.py"] + args_list
                    _m.cfg_check.config_check_entrypoint()
        return ep.exception.code

    def run_cli(self, command, args_list):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        with self.save_arguments():
            with self.redirect_output():
                with self.assertRaises(SystemExit) as ep:
                    import sys
                    sys.argv = ["fake.py"] + args_list
                    _m.cli.command.cli_command(
                        "Fake run for '{} {}'".format(
                            command,
                            " ".join(args_list)
                        ),
                        command
                    )
        return ep.exception.code

    @contextlib.contextmanager
    def redirect_output(self):
        save_stdout = sys.stdout
        save_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        logging.disable(logging.CRITICAL)
        yield
        sys.stdout = save_stdout
        sys.stderr = save_stderr

    @contextlib.contextmanager
    def save_arguments(self):
        _argv = deepcopy(sys.argv)
        yield
        sys.argv = _argv

    def _try_import(self, module_name):
        with self.redirect_output():
            _msg, _m = self._safe_import_module(module_name)

        self.assertEqual(
            len(_msg),
            0,
            "Error importing '{}': {}".format(
                module_name,
                _msg
            )
        )

        return _m
