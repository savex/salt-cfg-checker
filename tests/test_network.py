import os

from unittest.mock import patch

from tests.mocks import mocked_salt_post, mocked_salt_get
from tests.mocks import _res_dir
from tests.mocks import mocked_shell, _shell_salt_path
from tests.test_base import CfgCheckerTestBase

from cfg_checker.modules.network.network_errors import NetworkErrors


# Fake ErrorIndex
_ErrorIndex_path = "cfg_checker.helpers.errors.ErrorIndex"
_NErrors_path = "cfg_checker.modules.network.network_errors.NetworkErrors"

_fake_nerrors = NetworkErrors(folder="tests/res/fakeerrors")
_fake_nerrors._error_logs_folder_name = "tests/res/fakeerrors"


class TestNetworkModule(CfgCheckerTestBase):
    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    @patch(_NErrors_path, new=_fake_nerrors)
    def test_network_list(self, m_get, m_post, m_shell):
        _args = ["list"]
        _pm = "cfg_checker.modules.network.mapper.NetworkErrors"
        with patch(_pm, new=_fake_nerrors):
            _r_code = self.run_cli(
                "network",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-net {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    @patch(_NErrors_path, new=_fake_nerrors)
    def test_network_map(self, m_get, m_post, m_shell):
        _args = ["map"]
        with patch(
            "cfg_checker.modules.network.mapper.NetworkErrors",
            new=_fake_nerrors
        ):
            _r_code = self.run_cli(
                "network",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-net {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    @patch(_NErrors_path, new=_fake_nerrors)
    def test_network_check(self, m_get, m_post, m_shell):
        _args = ["check"]
        with patch(
            "cfg_checker.modules.network.checker.NetworkErrors",
            new=_fake_nerrors
        ):
            _r_code = self.run_cli(
                "network",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-net {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    @patch(_NErrors_path, new=_fake_nerrors)
    def test_network_report_html(self, m_get, m_post, m_shell):
        _fake_report = os.path.join(_res_dir, "fake.html")
        _args = ["report", "--html", _fake_report]
        _pc = "cfg_checker.modules.network.checker.NetworkErrors"
        with patch(_pc, new=_fake_nerrors):
            _r_code = self.run_cli(
                "network",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-net {}' command failed".format(" ".join(_args))
        )
