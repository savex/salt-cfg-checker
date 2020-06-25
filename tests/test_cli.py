from unittest import mock

from tests.test_base import CfgCheckerTestBase


class TestCliCommands(CfgCheckerTestBase):
    def test_do_cli_main_command(self):
        _module_name = 'cfg_checker.cfg_check'
        _m = self._try_import(_module_name)
        with self.save_arguments():
            with self.redirect_output():
                with self.assertRaises(SystemExit) as ep:
                    import sys
                    sys.argv = ["fake.py", "reclass", "list", "-p", "/tmp"]
                    _m.cfg_check.config_check_entrypoint()

        self.assertEqual(
            ep.exception.code,
            0,
            "'mcp-checker reclass list -p /tmp' command failed"
        )

    def test_do_cli_main_command_debug(self):
        _module_name = 'cfg_checker.cfg_check'
        _m = self._try_import(_module_name)
        with self.save_arguments():
            with self.redirect_output():
                with self.assertRaises(SystemExit) as ep:
                    import sys
                    sys.argv = [
                        "fake.py",
                        "-d",
                        "reclass",
                        "list",
                        "-p",
                        "/tmp"
                    ]
                    _m.cfg_check.config_check_entrypoint()

        self.assertEqual(
            ep.exception.code,
            0,
            "mcp-checker command failes"
        )

    def test_cli_main_unknown_argument(self):
        _module_name = 'cfg_checker.cfg_check'
        _m = self._try_import(_module_name)
        with self.redirect_output():
            with self.assertRaises(SystemExit) as ep:
                import sys
                sys.argv.append("reclass")
                sys.argv.append("list")
                _m.cfg_check.config_check_entrypoint()

        self.assertEqual(
            ep.exception.code,
            1,
            "Unknown argument not handled"
        )

    def test_do_cli_module_command(self):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        _command = "reclass"
        with self.save_arguments():
            with self.redirect_output():
                with self.assertRaises(SystemExit) as ep:
                    import sys
                    sys.argv = ["fake.py", "list", "-p", "/tmp"]
                    _m.cli.command.cli_command(
                        "Fake Reclass Comparer",
                        _command
                    )

        self.assertEqual(
            ep.exception.code,
            0,
            "Cli command execution failed"
        )

    def test_do_cli_module_command_with_error(self):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        _command = "reclass"
        with self.save_arguments():
            with self.redirect_output():
                with self.assertRaises(SystemExit) as ep:
                    import sys
                    sys.argv = ["fake.py", "list", "-p", "/notexistingfolder"]
                    _m.cli.command.cli_command(
                        "Fake Reclass Comparer",
                        _command
                    )

        self.assertEqual(
            ep.exception.code,
            1,
            "Cli command execution failed"
        )

    def test_cli_module_unknown_command(self):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        _fake_args = mock.MagicMock(name="FakeArgsClass")
        _command = "unknowncommand"
        with self.redirect_output():
            _r_value = _m.cli.command.execute_command(_fake_args, _command)

        self.assertEqual(
            _r_value,
            1,
            "Unknown command 'type' not handled"
        )

    def test_cli_module_no_type(self):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        _type = {}
        _command = "unknowncommand"
        with self.redirect_output():
            _r_value = _m.cli.command.execute_command(_type, _command)

        self.assertEqual(
            _r_value,
            1,
            "Unknown command not handled"
        )

    def test_cli_module_unknown_type(self):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        _fake_args = mock.MagicMock(name="FakeArgsClass")
        _command = "reclass"
        with self.redirect_output():
            _r_value = _m.cli.command.execute_command(_fake_args, _command)

        self.assertEqual(
            _r_value,
            1,
            "Unknown command not handled"
        )

    def test_cli_module_unknown_argument(self):
        _module_name = 'cfg_checker.cli.command'
        _m = self._try_import(_module_name)
        _command = "reclass"
        with self.redirect_output():
            with self.assertRaises(SystemExit) as ep:
                _m.cli.command.cli_command(
                    "Fake Reclass Comparer",
                    _command
                )

        self.assertEqual(
            ep.exception.code,
            1,
            "Unknown argument not handled"
        )
