# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Testing
```bash
# Run embedded unit tests
make test
# or directly:
./msrsync --selftest

# Run coverage analysis
make cov
make covhtml  # Generate HTML coverage report
```

### Code Quality
```bash
# Run linting
make lint
# This executes: pylint --disable=too-many-lines,line-too-long msrsync
```

### Installation
```bash
# Install to /usr/bin (or DESTDIR environment variable)
make install
```

### Benchmarking
```bash
# Run benchmarks (Linux only, requires root)
make bench
make benchshm  # Run benchmarks in /dev/shm
```

## Architecture Overview

msrsync is a single-file Python utility that wraps rsync to enable parallel file transfers. The codebase consists of two main scripts:
- `msrsync`: Python 2.6+ compatible version (primary)
- `msrsync3`: Python 3 version

### Core Design Patterns

1. **Multiprocessing Architecture**: Uses Python's multiprocessing module with a producer-consumer pattern. Files are grouped into "buckets" (limited by size/count), and each bucket is processed by a separate rsync process.

2. **Message Queue System**: Coordinates output between multiple processes using a central monitor process that handles progress reporting and error collection.

3. **Embedded Testing**: All unit tests are embedded within the main script and can be run via `--selftest`.

### Key Components

- **Options Parser**: Custom command-line parser based on bup project's options.py (embedded in the script)
- **File Crawler**: Recursively walks source directories and groups files into buckets
- **Worker Pool**: Manages parallel rsync processes with configurable concurrency
- **Monitor Process**: Handles progress reporting, error aggregation, and graceful shutdown

### Important Constraints

- Does not support remote source/destination directories (local paths only)
- Default rsync options: `-aS --numeric-ids`
- Python 2.6+ compatibility is maintained for RHEL6 support
- No external dependencies except rsync itself

## Development Notes

- The project is marked as not actively developed in README.md
- When modifying, ensure Python 2.6 compatibility for the main script
- Error codes are defined as constants (EMSRSYNC_*) at the top of the script
- All functionality is contained in a single file to simplify deployment