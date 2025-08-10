#!/usr/bin/env python

import os
import subprocess
import sys


def run_all_tests():
    """
    Run all test suites using pytest
    """
    # Change to the tests directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(test_dir)

    # Run pytest with verbose output
    result = subprocess.run([sys.executable, '-m', 'pytest', '-v', '.'], capture_output=False)
    return result.returncode


if __name__ == '__main__':
    sys.exit(run_all_tests())
