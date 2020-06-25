import os

from unittest.mock import patch

from tests.mocks import mocked_package_get
from tests.mocks import mocked_salt_post, mocked_salt_get
from tests.mocks import _res_dir
from tests.mocks import mocked_shell, _shell_salt_path
from tests.test_base import CfgCheckerTestBase

from cfg_checker.modules.packages.repos import RepoManager, ReposInfo


# init fake module path
_ReposInfo_path = "cfg_checker.modules.packages.repos.ReposInfo"
_RepoManager_path = "cfg_checker.modules.packages.repos.RepoManager"
# init fakes
_fakeReposInfo = ReposInfo(arch_folder=_res_dir)
_fakeRepoManager = RepoManager(
    arch_folder=_res_dir,
    info_class=_fakeReposInfo
)


class TestPackageModule(CfgCheckerTestBase):
    @patch('requests.get', side_effect=mocked_package_get)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    def test_build_repo_info(self, m_get):
        # init arguments
        _args = [
            "versions",
            "--url",
            "http://fakedomain.com",
            # "--tag",
            # "2099.0.0",
            "--build-repos"
        ]

        with patch(
            "cfg_checker.modules.packages.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_package_get)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    def test_build_repo_info_for_tag(self, m_get):
        # init arguments
        _args = [
            "versions",
            "--url",
            "http://fakedomain.com",
            "--tag",
            "2099.0.0"
        ]

        with patch(
            "cfg_checker.modules.packages.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_package_get)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    def test_package_versions_tags(self, m_get):
        _args = ["versions", "--list-tags"]
        with patch(
            "cfg_checker.modules.packages.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_package_get)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    def test_package_versions_show(self, m_get):
        _args = ["show", "fakepackage-m"]
        with patch(
            "cfg_checker.modules.packages.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_package_get)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    def test_package_versions_show_app(self, m_get):
        _args = ["show-app", "fakesection"]
        with patch(
            "cfg_checker.modules.packages.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    def test_package_report_html(self, m_get, m_post, m_shell):
        _fake_report = os.path.join(_res_dir, "fake.html")
        _args = ["report", "--html", _fake_report]
        with patch(
            "cfg_checker.modules.packages.checker.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    def test_package_report_html_full(self, m_get, m_post, m_shell):
        _fake_report = os.path.join(_res_dir, "fake.html")
        _args = ["report", "--full", "--html", _fake_report]
        with patch(
            "cfg_checker.modules.packages.checker.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    @patch('requests.get', side_effect=mocked_salt_get)
    @patch('requests.post', side_effect=mocked_salt_post)
    @patch(_ReposInfo_path, new=_fakeReposInfo)
    @patch(_RepoManager_path, new=_fakeRepoManager)
    @patch(_shell_salt_path, side_effect=mocked_shell)
    def test_package_report_csv(self, m_get, m_post, m_shell):
        _fake_report = os.path.join(_res_dir, "fake.csv")
        _args = ["report", "--csv", _fake_report]
        with patch(
            "cfg_checker.modules.packages.checker.RepoManager",
            new=_fakeRepoManager
        ):
            _r_code = self.run_cli(
                "packages",
                _args
            )
        self.assertEqual(
            _r_code,
            0,
            "'mcp-pkg {}' command failed".format(" ".join(_args))
        )

    def test_package_cmp_result_class(self):
        from cfg_checker.common.const import VERSION_OK, VERSION_UP, \
            VERSION_DOWN, VERSION_WARN
        from cfg_checker.common.const import ACT_NA, ACT_UPGRADE, \
            ACT_NEED_UP, ACT_NEED_DOWN, ACT_REPO

        _name = "cfg_checker.modules.packages.versions.VersionCmpResult"
        _message, _vcmp = self._safe_import_class(_name)
        _name = "cfg_checker.modules.packages.versions.DebianVersion"
        _message, dv = self._safe_import_class(_name)

        _ws = ": wrong status"
        _wa = ": wrong action"

        # Installed = Candidate = Release
        _b = "i = c = r"
        _i, _c, _r = dv("1:1.2-0u4"), dv("1:1.2-0u4"), dv("1:1.2-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_NA, _b + _wa)

        # Installed < Candidate, variations
        _b = "i < c, i = r"
        _i, _c, _r = dv("1:1.2-0u4"), dv("2:1.3-0u4"), dv("1:1.2-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_UPGRADE, _b + _wa)

        _b = "i < c, i > r"
        _i, _c, _r = dv("1:1.2-0u4"), dv("1:1.3-0u4"), dv("1:1.1-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_UP, _b + _ws)
        self.assertEqual(out.action, ACT_UPGRADE, _b + _wa)

        _b = "i < c, i < r, r < c"
        _i, _c, _r = dv("1:1.2-0u4"), dv("1:1.4-0u4"), dv("1:1.3-0u3")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_WARN, _b + _ws)
        self.assertEqual(out.action, ACT_NEED_UP, _b + _wa)

        _b = "i < c, i < r, r = c"
        _i, _c, _r = dv("1:1.2-0u4"), dv("1:1.4-0u4"), dv("1:1.4-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_WARN, _b + _ws)
        self.assertEqual(out.action, ACT_NEED_UP, _b + _wa)

        _b = "i < c, c < r"
        _i, _c, _r = dv("1:1.2-0u4"), dv("1:1.3-0u4"), dv("1:1.4-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_WARN, _b + _ws)
        self.assertEqual(out.action, ACT_REPO, _b + _wa)

        # Installed > Candidate, variations
        _b = "i > c, c = r"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.2-0u4"), dv("1:1.2-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_WARN, _b + _ws)
        self.assertEqual(out.action, ACT_NEED_DOWN, _b + _wa)

        _b = "i > c, c > r"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.2-0u4"), dv("0:1.2-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_UP, _b + _ws)
        self.assertEqual(out.action, ACT_NEED_DOWN, _b + _wa)

        _b = "i > c, c < r, r < i"
        _i, _c, _r = dv("1:1.3.1-0u4"), dv("1:1.2-0u4"), dv("1:1.3-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_UP, _b + _ws)
        self.assertEqual(out.action, ACT_REPO, _b + _wa)

        _b = "i > c, c < r, r = i"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.2-0u4"), dv("1:1.3-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_REPO, _b + _wa)

        _b = "i > c, i < r"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.2-0u4"), dv("2:1.4-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_DOWN, _b + _ws)
        self.assertEqual(out.action, ACT_REPO, _b + _wa)

        # Installed = Candidate, variations
        _b = "i = c, i < r"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.3-0u4"), dv("2:1.4-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_REPO, _b + _wa)

        _b = "i = c, i > r"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.3-0u4"), dv("1:1.1-0u2")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_WARN, _b + _ws)
        self.assertEqual(out.action, ACT_REPO, _b + _wa)

        _b = "i = c, i = r"
        _i, _c, _r = dv("1:1.3-0u4"), dv("1:1.3-0u4"), dv("1:1.3-0u4")
        out = _vcmp(_i, _c, _r)
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_NA, _b + _wa)

        # Installed vs Candidate, no release version
        _b = "i = c"
        _i, _c = dv("1:1.3-0u4"), dv("1:1.3-0u4")
        out = _vcmp(_i, _c, "")
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_NA, _b + _wa)

        _b = "i < c"
        _i, _c = dv("1:1.3-0u4"), dv("2:1.4-0u4")
        out = _vcmp(_i, _c, "")
        self.assertEqual(out.status, VERSION_OK, _b + _ws)
        self.assertEqual(out.action, ACT_UPGRADE, _b + _wa)

        _b = "i > c"
        _i, _c = dv("2:1.4-0~u4"), dv("1:1.2-0~u2")
        out = _vcmp(_i, _c, "")
        self.assertEqual(out.status, VERSION_UP, _b + _ws)
        self.assertEqual(out.action, ACT_NEED_DOWN, _b + _wa)
