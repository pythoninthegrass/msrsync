#!/usr/bin/env python3

import unittest
import os
import tempfile
import shutil
import shlex
from test_utils import import_msrsync3

msrsync3 = import_msrsync3()
_check_executables = msrsync3._check_executables
_create_fake_tree = msrsync3._create_fake_tree
_compare_trees = msrsync3._compare_trees
rmtree_onerror = msrsync3.rmtree_onerror
main = msrsync3.main


class TestSyncAPI(unittest.TestCase):
    """
    Test msrsync by directly calling python function
    It is redondant with TestSyncCLI but it makes coverage.py happy =)
    """

    # pylint: disable=too-many-public-methods
    def setUp(self):
        """ create a temporary fake tree """
        _check_executables()
        self.src = tempfile.mkdtemp(prefix='msrsync_testsync_')
        self.dst = tempfile.mkdtemp(prefix='msrsync_testsync_')
        _create_fake_tree(self.src, total_entries=1234, max_entries_per_level=123, max_depth=5, files_pct=95)

    def tearDown(self):
        """ remove the temporary fake tree """
        for path in self.src, self.dst:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=rmtree_onerror)

    def _msrsync_test_helper(self, options=""):
        """ msrsync test helper """
        cmdline = """msrsync %s %s %s""" % (options, self.src, self.dst)
        main(shlex.split(cmdline))
        self.assertTrue(_compare_trees(self.src, self.dst), "The source %s and destination %s tree are not equal." % (self.src, self.dst))

    def test_simple_msrsync_api(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper()

    def test_msrsync_api_2_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='-p 2')

    def test_msrsync_api_4_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='-p 4')

    def test_msrsync_api_8_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='-p 8')


if __name__ == '__main__':
    unittest.main()