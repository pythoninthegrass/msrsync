#!/usr/bin/env python

import pytest
from .test_utils import import_msrsync3

msrsync3 = import_msrsync3()
_check_executables = msrsync3._check_executables
_check_rsync_options = msrsync3._check_rsync_options
ERSYNC_OPTIONS_CHECK = msrsync3.ERSYNC_OPTIONS_CHECK


class TestRsyncOptionsChecker:
    """
    Test the rsync options checker
    """
    def setup_method(self):
        """ pytest setup """
        _check_executables()

    def test_rsync_wrong_options(self):
        """ test with wrong_options """
        with pytest.raises(SystemExit) as excinfo:
            rsync_options = "--this-is-fake"
            _check_rsync_options(rsync_options)
        assert excinfo.value.code == ERSYNC_OPTIONS_CHECK
