#!/usr/bin/env python3

import unittest
from test_utils import import_msrsync3

msrsync3 = import_msrsync3()
_check_executables = msrsync3._check_executables
_check_rsync_options = msrsync3._check_rsync_options
ERSYNC_OPTIONS_CHECK = msrsync3.ERSYNC_OPTIONS_CHECK


class TestRsyncOptionsChecker(unittest.TestCase):
    """
    Test the rsync options checker
    """
    def setUp(self):
        """ unittest setup """
        _check_executables()

    # pylint: disable=too-many-public-methods
    def test_rsync_wrong_options(self):
        """ test with wrong_options """
        try:
            rsync_options = "--this-is-fake"
            _check_rsync_options(rsync_options)
        except SystemExit as err:
            self.assertEqual(err.code, ERSYNC_OPTIONS_CHECK)
            return

        self.fail("Should have raised a SystemExit exception")


if __name__ == '__main__':
    unittest.main()