#!/usr/bin/env python

import pytest
from .test_utils import import_msrsync3

msrsync3 = import_msrsync3()
get_human_size = msrsync3.get_human_size
human_size = msrsync3.human_size


class TestHelpers:
    """
    Test the various function helpers
    """
    def test_get_human_size(self):
        """ convert bytes to human readable string """
        val = get_human_size(1024)
        assert val == '1.0 K'

    def test_get_human_size2(self):
        """ convert bytes to human readable string """
        val = get_human_size(1024*1024)
        assert val == '1.0 M'

    def test_human_size(self):
        """ convert human readable size to bytes """
        val = human_size("1024")
        assert val == 1024

    def test_human_size2(self):
        """ convert human readable size to bytes """
        val = human_size("1M")
        assert val == 1024*1024

    def test_human_size3(self):
        """ wrongly formatted size """
        val = human_size("10KK")
        assert val is None

    def test_human_size4(self):
        """ bad suffix  """
        val = human_size("10Q")
        assert val is None
