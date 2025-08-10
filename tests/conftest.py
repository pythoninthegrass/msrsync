"""
Pytest configuration and fixtures for msrsync tests
"""

import os
import signal
import sys
import tempfile
import pytest
from .test_utils import import_msrsync3

msrsync3 = import_msrsync3()


@pytest.fixture(scope="session", autouse=True)
def signal_handler_session():
    """
    Session-scoped fixture that sets up signal handling for the entire test run
    This ensures that if tests are interrupted, they clean up properly
    """
    temp_dirs = []
    interrupted = False

    def handle_signal(signum, frame):
        """Handle test interruption signals"""
        nonlocal interrupted
        if interrupted:
            # If we're already cleaning up, force exit
            print("\nForced exit during cleanup", file=sys.stderr)
            sys.exit(128 + signum)

        interrupted = True
        signal_name = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}.get(signum, f"signal {signum}")
        print(f"\nTest suite interrupted by {signal_name}. Cleaning up temporary directories...", file=sys.stderr)

        # Clean up temporary directories
        cleaned = 0
        for temp_dir in temp_dirs[:]:  # Copy list to avoid modification during iteration
            if os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir, onerror=msrsync3.rmtree_onerror)
                    cleaned += 1
                    temp_dirs.remove(temp_dir)
                except Exception as e:
                    print(f"Warning: Failed to clean up {temp_dir}: {e}", file=sys.stderr)

        if cleaned > 0:
            print(f"Cleaned up {cleaned} temporary directories", file=sys.stderr)

        # Let pytest handle the interruption
        raise KeyboardInterrupt()

    # Save original handlers
    old_handlers = {}
    for sig in [signal.SIGINT, signal.SIGTERM]:
        old_handlers[sig] = signal.signal(sig, handle_signal)

    # Make temp_dirs accessible to other fixtures
    signal_handler_session.temp_dirs = temp_dirs
    signal_handler_session.interrupted = lambda: interrupted

    try:
        yield
    finally:
        # Restore original signal handlers
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)

        # Final cleanup of any remaining temp directories
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir, onerror=msrsync3.rmtree_onerror)
                except Exception:
                    pass  # Ignore cleanup errors at this point


@pytest.fixture
def managed_temp_dir(signal_handler_session):
    """
    Fixture that creates a temporary directory and registers it for cleanup
    on test interruption. This is useful for integration tests that create
    large amounts of test data.
    """
    temp_dir = tempfile.mkdtemp(prefix='msrsync_test_')

    # Register for cleanup in case of interruption
    if hasattr(signal_handler_session, 'temp_dirs'):
        signal_handler_session.temp_dirs.append(temp_dir)

    yield temp_dir

    # Normal cleanup
    import shutil

    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir, onerror=msrsync3.rmtree_onerror)
        except Exception as e:
            print(f"Warning: Failed to clean up {temp_dir}: {e}", file=sys.stderr)

    # Remove from interrupt cleanup list
    if hasattr(signal_handler_session, 'temp_dirs') and temp_dir in signal_handler_session.temp_dirs:
        signal_handler_session.temp_dirs.remove(temp_dir)


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "integration: marks tests as integration tests (may require special setup)")
    config.addinivalue_line("markers", "slow: marks tests as slow running (may be skipped in CI)")


def pytest_collection_modifyitems(config, items):
    """Automatically skip integration tests if not explicitly requested"""
    # If -m integration is specified, don't skip anything
    if config.getoption("-m") and "integration" in config.getoption("-m"):
        return

    # Otherwise, skip integration tests unless explicitly running them
    skip_integration = pytest.mark.skip(reason="integration test (use -m integration to run)")
    for item in items:
        if "integration" in item.keywords:
            # Check if we're running tests in a CI environment or with special flags
            if not (os.getenv("CI") or config.getoption("--run-integration", False)):
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption("--run-integration", action="store_true", default=False, help="Run integration tests")
    parser.addoption("--timeout", action="store", default=60, type=int, help="Timeout for individual tests (default: 60 seconds)")
