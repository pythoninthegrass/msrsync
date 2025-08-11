# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Testing

#### Synthetic

- Synthetic tests should always last long enough with enough files to reproduce real world conditions
  - `create_test_directory(src_dir, num_files=1000, size=102400)`  # 1000 files, 100KB each
  - Let it run for a bit: `time.sleep(0.5)`

```bash
# TODO: migrate to taskfile
# Run embedded unit tests
# make test
# or directly:
./msrsync3 --selftest

# TODO: migrate to taskfile
# Run coverage analysis
# make cov
# make covhtml  # Generate HTML coverage report

# Run tests via uv
uv run pytest tests/ -v -m "not integration"  # Run unit tests
uv run pytest tests/ -v -m "integration"      # Run integration tests (requires rsync and multiprocessing)
```

#### Organic

- Run on the Beelink ME mini via `ssh me-mini`
  - `msrsync` is symlinked to `~/git/msrsync/msrsync3`
- Avoid interactive terminal issues: 
  - `ssh me-mini "/root/.local/share/mise/installs/python/3.13.5/bin/python /root/git/msrsync/msrsync3 -p 4 -P -s 2G /mnt/synology-shares/ /mnt/user/shares/`

### Code Quality

```bash
# TODO: migrate to taskfile
# Run linting
# make lint
```

### Installation

```bash
# TODO: migrate to taskfile
# Install to /usr/bin (or DESTDIR environment variable)
# make install
```

### Benchmarking

```bash
# Run benchmark tests (requires root for full functionality)
uv run python tests/test_benchmarks.py

# Run benchmarks with specific source and destination and create test data
uv run python tests/test_benchmarks.py --source /tmp/large_test --dest /tmp/dest_test --create-data 50000

# Run integration tests including benchmarks
uv run pytest tests/ -v -m "integration"

# Run performance benchmarking functions directly
uv run python -c "from tests.test_benchmarks import benchmark_performance; benchmark_performance(total_entries=1000)"
uv run python -c "from tests.test_benchmarks import benchmark_shm; benchmark_shm(total_entries=1000)"
```

## Architecture Overview

msrsync is a single-file Python utility that wraps rsync to enable parallel file transfers. The codebase consists of two main scripts:
- `msrsync3`: Python 3 version
- `msrsync`: Python 2.6+ compatible version (deprecated)
  - Ignore this version entirely outside of reference implementation

### Core Design Patterns

1. **Multiprocessing Architecture**: Uses Python's multiprocessing module with a producer-consumer pattern. Files are grouped into "buckets" (limited by size/count), and each bucket is processed by a separate rsync process.

2. **Message Queue System**: Coordinates output between multiple processes using a central monitor process that handles progress reporting and error collection.

3. **Separated Testing**: Unit tests are in the `tests/` directory and can be run via `--selftest` or directly with pytest. Benchmarking has been moved to `tests/test_benchmarks.py`.

### Key Components

- **Options Parser**: Custom command-line parser based on bup project's options.py (embedded in the script)
- **File Crawler**: Recursively walks source directories and groups files into buckets
- **Worker Pool**: Manages parallel rsync processes with configurable concurrency
- **Monitor Process**: Handles progress reporting, error aggregation, and graceful shutdown

### Important Constraints

- Does not support remote source/destination directories (local paths only)
- Default rsync options: `-aS --numeric-ids`

## Development Notes

- When testing synced files/directories, always use `/tmp` as the parent directory
  - e.g., `/tmp/test_src`, `/tmp/test_dest`
- Error codes are defined as constants (EMSRSYNC_*) at the top of the script
- All functionality is contained in a single file to simplify deployment
- Use `uv run` for all virtual environment calls
- Lint python files with
  - `ruff check <FILE> --unsafe-fixes --fix --diff`
  - `ruff format <FILE>`
- Respect `.editorconfig` settings
- Use `markdownlint -c .markdownlint.jsonc <MARKDOWN_FILE>` when editing markdown
