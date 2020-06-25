import inspect
import os
import sys
from unittest import mock


from tests.test_base import CfgCheckerTestBase
from tests.test_base import tests_dir

gzip_filename = "textfile.txt.gz"
fake_gzip_file_path = os.path.join(tests_dir, 'res', gzip_filename)
_patch_buf = []
with open(fake_gzip_file_path, 'rb') as _f:
    _patch_buf = _f.read()


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, content, status_code):
            self.content = content
            self.status_code = status_code

        def content(self):
            return self.content

    if args[0] == fake_gzip_file_path:
        return MockResponse(_patch_buf, 200)

    return MockResponse(None, 404)


class TestCommonModules(CfgCheckerTestBase):
    def test_exceptions(self):
        _m = self._try_import("cfg_checker.common.exception")
        # Get all classes from the exceptions module
        _classes = inspect.getmembers(
            sys.modules[_m.common.exception.__name__],
            inspect.isclass
        )
        # Create instance for all detected classes except for the Base one
        _errors = []
        for _name, _class in _classes:
            if _name.startswith("CheckerBase"):
                continue
            _, _msg = self._safe_run(_class, "Fake exception message")
            if _msg:
                _errors.append(_msg)

        self.assertEqual(
            len(_errors),
            0,
            "Invalid Exception classes detected: \n{}".format(
                "\n".join(_errors)
            )
        )

    def test_file_utils(self):
        # File operations itself is not to be tested
        # Only classes that provide api methods
        # I.e. no exceptions - no errors,
        # file contents is not to be checked, only return types
        _m = self._try_import("cfg_checker.common.file_utils")
        _futils = _m.common.file_utils
        _filename = "/tmp/fakefile.txt"
        _fakestr = "Fake String in the file"
        _errors = []

        # write_str_to_file
        _, _msg = self._safe_run(
            _futils.write_str_to_file,
            _filename,
            _fakestr
        )
        if _msg:
            _errors.append(_msg)

        # append_str_to_file
        _, _msg = self._safe_run(
            _futils.append_str_to_file,
            _filename,
            _fakestr
        )
        if _msg:
            _errors.append(_msg)

        # remove_file
        _, _msg = self._safe_run(_futils.remove_file, _filename)
        if _msg:
            _errors.append(_msg)

        # write_lines_to_file
        _, _msg = self._safe_run(
            _futils.write_lines_to_file,
            _filename,
            [_fakestr]
        )
        if _msg:
            _errors.append(_msg)

        # append_lines_to_file
        _, _msg = self._safe_run(
            _futils.append_lines_to_file,
            _filename,
            [_fakestr]
        )
        if _msg:
            _errors.append(_msg)

        # append_line_to_file
        _, _msg = self._safe_run(
            _futils.append_line_to_file,
            _filename,
            _fakestr
        )
        if _msg:
            _errors.append(_msg)

        # read_file
        _r, _msg = self._safe_run(_futils.read_file, _filename)
        if _msg:
            _errors.append(_msg)
        self.assertNotEqual(
            len(_r),
            0,
            "Empty buffer returned by 'read_file'"
        )

        # read_file_as_lines
        _r, _msg = self._safe_run(_futils.read_file_as_lines, _filename)
        if _msg:
            _errors.append(_msg)
        self.assertNotEqual(
            len(_r),
            0,
            "Empty buffer returned by 'read_file_as_lines'"
        )
        self.assertIsInstance(
            _r,
            list,
            "Non-list type returned by 'read_file_as_lines'"
        )
        # get_file_info_fd
        with open(_filename) as _fd:
            _r, _msg = self._safe_run(_futils.get_file_info_fd, _fd)
            if _msg:
                _errors.append(_msg)
            self.assertIsInstance(
                _r,
                dict,
                "Non-dict type returned by get_file_info_fd"
            )
            _, _msg = self._safe_run(_futils.remove_file, _filename)

        # get_gzipped_file

        _folder = "/tmp/cfgcheckertmpfolder"
        # ensure_folder_exists
        _, _msg = self._safe_run(_futils.ensure_folder_exists, _folder)
        if _msg:
            _errors.append(_msg)
        _, _msg = self._safe_run(_futils.ensure_folder_exists, _folder)
        if _msg:
            _errors.append(_msg)

        # ensure_folder_removed
        _, _msg = self._safe_run(_futils.ensure_folder_removed, _folder)
        if _msg:
            _errors.append(_msg)
        _, _msg = self._safe_run(_futils.ensure_folder_removed, _folder)
        if _msg:
            _errors.append(_msg)

        self.assertEqual(
            len(_errors),
            0,
            "Invalid file operations: \n{}".format(
                "\n".join(_errors)
            )
        )

    @mock.patch(
        'requests.get',
        side_effect=mocked_requests_get
    )
    def test_get_gzip_file(self, mock_get):
        _m = self._try_import("cfg_checker.common.file_utils")
        _futils = _m.common.file_utils
        _fakecontent = b"fakecontent\n"
        _errors = []

        # Call the method with patched data
        _buf, _msg = self._safe_run(
            _futils.get_gzipped_file,
            fake_gzip_file_path
        )
        if _msg:
            _errors.append(_msg)

        self.assertNotEqual(
            len(_buf),
            0,
            "Empty buffer returned by 'get_gzipped_file'"
        )
        self.assertEqual(
            _buf,
            _fakecontent,
            "Incorrect content returned by 'get_gzipped_file'"
        )
