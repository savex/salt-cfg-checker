from tests.test_base import CfgCheckerTestBase


class TestEntrypoints(CfgCheckerTestBase):
    def test_entry_mcp_checker(self):
        _module_name = 'cfg_checker.cfg_check'
        with self.redirect_output():
            _msg, _m = self._safe_import_module(_module_name)

        self.assertEqual(
            len(_msg),
            0,
            "Error importing '{}': {}".format(
                _module_name,
                _msg
            )
        )

        with self.redirect_output():
            with self.assertRaises(SystemExit) as ep:
                _m.cfg_check.config_check_entrypoint()
        # empty run should return code 1
        self.assertEqual(
            ep.exception.code,
            1,
            "mcp-checker has unexpected exit code: {}".format(
                ep.exception.code
            )
        )

    def test_entry_packages(self):
        _module_name = 'cfg_checker.cli.packages'
        with self.redirect_output():
            _msg, _m = self._safe_import_module(_module_name)

        self.assertEqual(
            len(_msg),
            0,
            "Error importing '{}': {}".format(
                _module_name,
                _msg
            )
        )

        with self.redirect_output():
            with self.assertRaises(SystemExit) as ep:
                _m.cli.packages.entrypoint()
        # empty run should return code 1
        self.assertEqual(
            ep.exception.code,
            1,
            "packages has unexpected exit code: {}".format(ep.exception.code)
        )

    def test_entry_network(self):
        _module_name = 'cfg_checker.cli.network'
        with self.redirect_output():
            _msg, _m = self._safe_import_module(_module_name)

        self.assertEqual(
            len(_msg),
            0,
            "Error importing '{}': {}".format(
                _module_name,
                _msg
            )
        )

        with self.redirect_output():
            with self.assertRaises(SystemExit) as ep:
                _m.cli.network.entrypoint()
        # empty run should return code 1
        self.assertEqual(
            ep.exception.code,
            1,
            "network has unexpected exit code: {}".format(ep.exception.code)
        )

    def test_entry_reclass(self):
        _module_name = 'cfg_checker.cli.reclass'
        with self.redirect_output():
            _msg, _m = self._safe_import_module(_module_name)

        self.assertEqual(
            len(_msg),
            0,
            "Error importing '{}': {}".format(
                _module_name,
                _msg
            )
        )

        with self.redirect_output():
            with self.assertRaises(SystemExit) as ep:
                _m.cli.reclass.entrypoint()
        # empty run should return code 1
        self.assertEqual(
            ep.exception.code,
            1,
            "reclass has unexpected exit code: {}".format(ep.exception.code)
        )
