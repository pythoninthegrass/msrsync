#!/usr/bin/env python

"""
Utility functions for importing msrsync3 module from tests
"""

import importlib.util
import os
import sys


def import_msrsync3():
    """Import the msrsync3 module from the parent directory"""
    msrsync3_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "msrsync3")

    if not os.path.exists(msrsync3_path):
        raise FileNotFoundError("msrsync3 file not found at %s" % msrsync3_path)

    # Read and execute the file directly since it doesn't have .py extension
    with open(msrsync3_path) as f:
        code = f.read()

    # Create a module object
    import types
    msrsync3 = types.ModuleType('msrsync3')
    msrsync3.__file__ = msrsync3_path

    # Execute the code in the module namespace
    exec(code, msrsync3.__dict__)

    return msrsync3
