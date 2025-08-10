#!/usr/bin/env python3

import unittest
from test_helpers import TestHelpers
from test_options_parser import TestOptionsParser
from test_rsync_options_checker import TestRsyncOptionsChecker
from test_sync_api import TestSyncAPI
from test_sync_cli import TestSyncCLI


def run_all_tests():
    """
    Run all test suites
    """
    suite = unittest.TestSuite()

    tests = [TestHelpers,
             TestOptionsParser,
             TestRsyncOptionsChecker,
             TestSyncAPI,
             TestSyncCLI]

    for test in tests:
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(test))

    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    run_all_tests()