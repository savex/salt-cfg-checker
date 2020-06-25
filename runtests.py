import os
import shutil
import unittest

from unittest import TextTestResult, TextTestRunner
from tests.test_base import tests_dir
from tests.test_packages import _res_dir


class MyTestResult(TextTestResult):
    def getDescription(self, test):
        # return super().getDescription(test)
        doc_first_line = test.shortDescription()
        if self.descriptions and doc_first_line:
            return '\n'.join((str(test), doc_first_line))
        else:
            # return str(test)
            return "{}.{}.{}".format(
                test.__class__.__module__,
                test.__class__.__name__,
                test._testMethodName
            )


class MyTestRunner(TextTestRunner):
    resultclass = MyTestResult


def _cleanup():
    _fpath = [
        "repo.info.tgz",
        "repo.versions.tgz",
        "pkg.descriptions.tgz"
    ]
    for _p in _fpath:
        _fp = os.path.join(_res_dir, _p)
        if os.path.exists(_fp):
            os.remove(_fp)

    _ferr = os.path.join(_res_dir, "fakeerrors")
    if os.path.exists(_ferr):
        shutil.rmtree(_ferr)


if __name__ == '__main__':
    # remove old files if exists
    _cleanup()

    # start tests
    suite = unittest.TestLoader().discover(tests_dir, "test_*", tests_dir)
    runner = MyTestRunner(verbosity=3)
    runner.run(suite)

    # cleanup after testrun
    _cleanup()
