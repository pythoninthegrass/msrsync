#!/usr/bin/env python3

import unittest
import shlex
from test_utils import import_msrsync3

msrsync3 = import_msrsync3()
parse_cmdline = msrsync3.parse_cmdline
EOPTION_PARSER = msrsync3.EOPTION_PARSER
DEFAULT_RSYNC_OPTIONS = msrsync3.DEFAULT_RSYNC_OPTIONS


class TestOptionsParser(unittest.TestCase):
    """
    Test the command line parsing
    """
    # pylint: disable=too-many-public-methods
    def test_nooption(self):
        """ parse cmdline without argument"""
        try:
            cmdline = shlex.split("msrsync")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_justrsync(self):
        """ parse cmdline with only --rsync option"""
        try:
            cmdline = shlex.split("msrsync --rsync")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_badsize(self):
        """ parse cmdline with a bad size"""
        try:
            cmdline = shlex.split("msrsync -s abcde src dest")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_badsize2(self):
        """ parse cmdline with a bad size"""
        try:
            cmdline = shlex.split("msrsync -s abcde src dest")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")


    def test_bad_filesnumber(self):
        """ parse cmdline with a bad size"""
        try:
            cmdline = shlex.split("msrsync -f abcde src dest")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_only_src(self):
        """ parse cmdline with only a source dir"""
        try:
            cmdline = shlex.split("msrsync src")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_src_dst(self):
        """ test a basic and valid command line """
        cmdline = shlex.split("msrsync src dst")
        opt, srcs, dst = parse_cmdline(cmdline)
        self.assertEqual(opt.rsync, DEFAULT_RSYNC_OPTIONS)
        self.assertEqual(srcs, ["src"])
        self.assertEqual(dst, "dst")

    def test_src_multiple_dst(self):
        """ test a command line with multiple sources """
        cmdline = shlex.split("msrsync src1 src2 dst")
        opt, srcs, dst = parse_cmdline(cmdline)
        self.assertEqual(opt.rsync, DEFAULT_RSYNC_OPTIONS)
        self.assertEqual(srcs, ["src1", "src2"])
        self.assertEqual(dst, "dst")

    def test_src_dst_rsync(self):
        """ test a basic and valid command line with rsync option """
        cmdline = shlex.split("""msrsync --rsync "--numeric-ids" src dst""")
        opt, srcs, dst = parse_cmdline(cmdline)
        self.assertEqual(opt.rsync, "--numeric-ids")
        self.assertEqual(srcs, ["src"])
        self.assertEqual(dst, "dst")

    def test_src_multiple_dst_rsync(self):
        """ test a command line with multiple sources """
        cmdline = shlex.split("""msrsync --rsync "--numeric-ids" src1 src2 dst""")
        opt, srcs, dst = parse_cmdline(cmdline)
        self.assertEqual(opt.rsync, "--numeric-ids")
        self.assertEqual(srcs, ["src1", "src2"])
        self.assertEqual(dst, "dst")

    def test_src_dest_empty_rsync(self):
        """ test a basic and valid command line, but with empty rsync option """
        try:
            cmdline = shlex.split("msrsync --rsync src dst")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_rsync_delete(self):
        """ command line with --rsync option that contains --delete """
        try:
            cmdline = shlex.split("""msrsync --rsync "--delete" dst""")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_rsync_delete2(self):
        """ command line with --rsync option that contains --delete """
        try:
            cmdline = shlex.split("""msrsync --rsync "-a --numeric-ids --delete" src dst""")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")

    def test_rsync_delete3(self):
        """ command line with -r option that contains --delete """
        try:
            cmdline = shlex.split("""msrsync -r "-a --numeric-ids --delete" src dst""")
            parse_cmdline(cmdline)
        except SystemExit as err:
            self.assertEqual(err.code, EOPTION_PARSER)
            return

        self.fail("Should have raised a SystemExit exception")


if __name__ == '__main__':
    unittest.main()