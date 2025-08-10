#!/usr/bin/env python

import pytest
import shlex
from .test_utils import import_msrsync3

msrsync3 = import_msrsync3()
parse_cmdline = msrsync3.parse_cmdline
EOPTION_PARSER = msrsync3.EOPTION_PARSER
DEFAULT_RSYNC_OPTIONS = msrsync3.DEFAULT_RSYNC_OPTIONS


class TestOptionsParser:
    """
    Test the command line parsing
    """

    def test_nooption(self):
        """parse cmdline without argument"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync")
            parse_cmdline(cmdline)
        assert excinfo.value.code == 0

    def test_justrsync(self):
        """parse cmdline with only --rsync option"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync --rsync")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_badsize(self):
        """parse cmdline with a bad size"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync -s abcde src dest")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_badsize2(self):
        """parse cmdline with a bad size"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync -s abcde src dest")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_bad_filesnumber(self):
        """parse cmdline with a bad size"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync -f abcde src dest")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_only_src(self):
        """parse cmdline with only a source dir"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync src")
            parse_cmdline(cmdline)
        assert excinfo.value.code == 0

    def test_src_dst(self):
        """test a basic and valid command line"""
        cmdline = shlex.split("msrsync src dst")
        opt, srcs, dst = parse_cmdline(cmdline)
        assert opt.rsync == DEFAULT_RSYNC_OPTIONS
        assert srcs == ["src"]
        assert dst == "dst"

    def test_src_multiple_dst(self):
        """test a command line with multiple sources"""
        cmdline = shlex.split("msrsync src1 src2 dst")
        opt, srcs, dst = parse_cmdline(cmdline)
        assert opt.rsync == DEFAULT_RSYNC_OPTIONS
        assert srcs == ["src1", "src2"]
        assert dst == "dst"

    def test_src_dst_rsync(self):
        """test a basic and valid command line with rsync option"""
        cmdline = shlex.split("""msrsync --rsync "--numeric-ids" src dst""")
        opt, srcs, dst = parse_cmdline(cmdline)
        assert opt.rsync == "--numeric-ids"
        assert srcs == ["src"]
        assert dst == "dst"

    def test_src_multiple_dst_rsync(self):
        """test a command line with multiple sources"""
        cmdline = shlex.split("""msrsync --rsync "--numeric-ids" src1 src2 dst""")
        opt, srcs, dst = parse_cmdline(cmdline)
        assert opt.rsync == "--numeric-ids"
        assert srcs == ["src1", "src2"]
        assert dst == "dst"

    def test_src_dest_empty_rsync(self):
        """test a basic and valid command line, but with empty rsync option"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("msrsync --rsync src dst")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_rsync_delete(self):
        """command line with --rsync option that contains --delete"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("""msrsync --rsync "--delete" dst""")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_rsync_delete2(self):
        """command line with --rsync option that contains --delete"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("""msrsync --rsync "-a --numeric-ids --delete" src dst""")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER

    def test_rsync_delete3(self):
        """command line with -r option that contains --delete"""
        with pytest.raises(SystemExit) as excinfo:
            cmdline = shlex.split("""msrsync -r "-a --numeric-ids --delete" src dst""")
            parse_cmdline(cmdline)
        assert excinfo.value.code == EOPTION_PARSER
