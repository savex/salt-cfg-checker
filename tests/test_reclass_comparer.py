import os

from tests.mocks import _res_dir
from tests.test_base import CfgCheckerTestBase


class TestReclassModule(CfgCheckerTestBase):
    def test_reclass_list(self):
        _models_dir = os.path.join(_res_dir, "models")
        _args = ["list", "-p", _models_dir]

        _r_code = self.run_cli(
            "reclass",
            _args
        )
        self.assertEqual(
            _r_code,
            0,
            "'cmp-reclass {}' command failed".format(" ".join(_args))
        )

    def test_reclass_compare(self):
        _models_dir = os.path.join(_res_dir, "models")
        _model01 = os.path.join(_models_dir, "model01")
        _model02 = os.path.join(_models_dir, "model02")
        _report_path = os.path.join(_res_dir, "_fake.html")
        _args = [
            "diff",
            "--model1",
            _model01,
            "--model2",
            _model02,
            "--html",
            _report_path
        ]

        _r_code = self.run_cli(
            "reclass",
            _args
        )
        self.assertEqual(
            _r_code,
            0,
            "'cmp-reclass {}' command failed".format(" ".join(_args))
        )
