#!/usr/bin/env python3

import unittest
from test_utils import import_msrsync3

msrsync3 = import_msrsync3()
get_human_size = msrsync3.get_human_size
human_size = msrsync3.human_size


class TestHelpers(unittest.TestCase):
    """
    Test the various function helpers
    """
    # pylint: disable=too-many-public-methods
    def test_get_human_size(self):
        """ convert bytes to human readable string """
        val = get_human_size(1024)
        self.assertEqual(val, '1.0 K')

    def test_get_human_size2(self):
        """ convert bytes to human readable string """
        val = get_human_size(1024*1024)
        self.assertEqual(val, '1.0 M')

    def test_human_size(self):
        """ convert human readable size to bytes """
        val = human_size("1024")
        self.assertEqual(val, 1024)

    def test_human_size2(self):
        """ convert human readable size to bytes """
        val = human_size("1M")
        self.assertEqual(val, 1024*1024)

    def test_human_size3(self):
        """ wrongly formatted size """
        val = human_size("10KK")
        self.assertEqual(val, None)

    def test_human_size4(self):
        """ bad suffix  """
        val = human_size("10Q")
        self.assertEqual(val, None)


if __name__ == '__main__':
    unittest.main()