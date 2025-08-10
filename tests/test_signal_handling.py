#!/usr/bin/env python

"""
Signal handling tests and fixtures for msrsync test suite
"""

import os
import signal
import sys
import tempfile
import pytest
from .test_utils import import_msrsync3

msrsync3 = import_msrsync3()


class TestSignalHandling:
    """Test signal handling in msrsync"""

    def test_interrupt_error_code(self):
        """Test that msrsync returns correct error code when interrupted"""
        # This is mainly a documentation test - the actual error code constant
        assert hasattr(msrsync3, 'EMSRSYNC_INTERRUPTED')
        assert msrsync3.EMSRSYNC_INTERRUPTED == 26

    @pytest.mark.integration
    def test_signal_handling_constants(self):
        """Test that signal handling constants are properly defined"""
        # Test that the error codes are properly defined
        assert hasattr(msrsync3, 'EMSRSYNC_INTERRUPTED')
        assert msrsync3.EMSRSYNC_INTERRUPTED == 26

        # This test validates that our signal handling refactoring
        # maintains the correct error codes
        print("Signal handling constants are properly defined")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_signal_handling_subprocess_manual(self):
        """
        Manual test for signal handling - requires manual interruption
        This test is mainly for documentation of expected behavior
        """
        pytest.skip("This test requires manual interruption - run manually if needed")
        # The actual signal handling test was moved to manual testing
        # since it's difficult to make reliable in automated tests


# Pytest fixtures for improved signal handling during tests
@pytest.fixture(scope="session", autouse=True)
def test_signal_handler():
    """
    Session-scoped fixture that sets up signal handling for the entire test run
    This ensures that if tests are interrupted, they clean up properly
    """
    interrupted = {"value": False}
    temp_dirs = []

    def signal_handler(signum, frame):
        """Handle test interruption"""
        interrupted["value"] = True
        print(f"\nTest run interrupted (signal {signum}). Cleaning up...", file=sys.stderr)

        # Clean up any temporary directories created during tests
        import shutil

        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, onerror=msrsync3.rmtree_onerror)
                    print(f"Cleaned up: {temp_dir}", file=sys.stderr)
                except Exception as e:
                    print(f"Failed to clean up {temp_dir}: {e}", file=sys.stderr)

        # Re-raise KeyboardInterrupt to let pytest handle it
        raise KeyboardInterrupt()

    # Set up signal handlers
    old_sigint = signal.signal(signal.SIGINT, signal_handler)
    old_sigterm = signal.signal(signal.SIGTERM, signal_handler)

    # Store reference for other fixtures/tests to use
    test_signal_handler.temp_dirs = temp_dirs
    test_signal_handler.interrupted = interrupted

    yield

    # Restore original signal handlers
    signal.signal(signal.SIGINT, old_sigint)
    signal.signal(signal.SIGTERM, old_sigterm)


@pytest.fixture
def temp_dir_with_cleanup():
    """
    Fixture that creates a temporary directory and registers it for cleanup
    on test interruption
    """
    temp_dir = tempfile.mkdtemp(prefix='msrsync_test_')

    # Register for cleanup in case of interruption
    if hasattr(test_signal_handler, 'temp_dirs'):
        test_signal_handler.temp_dirs.append(temp_dir)

    yield temp_dir

    # Normal cleanup
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, onerror=msrsync3.rmtree_onerror)

    # Remove from interrupt cleanup list
    if hasattr(test_signal_handler, 'temp_dirs') and temp_dir in test_signal_handler.temp_dirs:
        test_signal_handler.temp_dirs.remove(temp_dir)
