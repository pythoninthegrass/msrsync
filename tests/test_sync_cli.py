#!/usr/bin/env python3

import unittest
import sys
import os
import tempfile
import shutil
from test_utils import import_msrsync3

msrsync3 = import_msrsync3()
_check_executables = msrsync3._check_executables
_create_fake_tree = msrsync3._create_fake_tree
_compare_trees = msrsync3._compare_trees
rmtree_onerror = msrsync3.rmtree_onerror
run = msrsync3.run
RSYNC_EXE = msrsync3.RSYNC_EXE
DEFAULT_RSYNC_OPTIONS = msrsync3.DEFAULT_RSYNC_OPTIONS


class TestSyncCLI(unittest.TestCase):
    """
    Test the synchronisation process using the commmand line interface
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
        msrsync3_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "msrsync3")
        cmd = "%s %s %s %s %s" % (sys.executable, msrsync3_path, options, self.src + os.sep, self.dst)
        ret, _, _, timeout, _ = run(cmd, timeout_sec=60)
        self.assertTrue(not timeout, "The msrsync command has timeouted.")
        self.assertEqual(ret, 0, "The msrsync command has failed: %s" % cmd)
        self.assertTrue(_compare_trees(self.src, self.dst), "The source %s and destination %s tree are not equal." % (self.src, self.dst))


    def test_simple_rsync(self):
        """ test simple rsync synchronisation """
        cmd = "%s %s %s %s" % (RSYNC_EXE, DEFAULT_RSYNC_OPTIONS, self.src + os.sep, self.dst)
        ret, _, _, timeout, _ = run(cmd, timeout_sec=60)
        self.assertTrue(not timeout, "The rsync command has timeouted.")
        self.assertEqual(ret, 0, "The rsync command has failed.")
        self.assertTrue(_compare_trees(self.src, self.dst), "The source and destination tree are not equal. %s %s" % (self.src, self.dst))

    def test_simple_msrsync_cli(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper()

    def test_simple_msrsync_progress_cli(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='--progress')

    def test_msrsync_progress_cli_2_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='--progress -p 2')

    def test_msrsync_cli_2_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='-p 2')

    def test_msrsync_cli_4_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='-p 4')

    def test_msrsync_cli_8_processes(self):
        """ test simple msrsync synchronisation """
        self._msrsync_test_helper(options='-p 8')


if __name__ == '__main__':
    unittest.main()