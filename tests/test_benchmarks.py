#!/usr/bin/env python

"""
Network-aware benchmarking suite for msrsync optimization

Tests specifically designed for:
- Mechanical source drives (NAS)
- Network bottlenecks (1Gbps destination, 2Gbps source)
- Limited CPU/RAM (4-core, 12GB)
- fd vs os.walk performance
- Compression benefits
- Process scaling limits
"""

import argparse
import concurrent.futures
import contextlib
import json
import os
import psutil
import pytest
import queue
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Handle both standalone execution and pytest import
try:
    from .test_utils import import_msrsync3

    msrsync3 = import_msrsync3()
except ImportError:
    # Standalone execution - import msrsync3 directly
    import importlib.util

    msrsync3_path = Path(__file__).parent.parent / "msrsync3"
    if msrsync3_path.exists():
        spec = importlib.util.spec_from_file_location("msrsync3", msrsync3_path)
        if spec and spec.loader:
            msrsync3 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(msrsync3)
        else:
            msrsync3 = None
    else:
        msrsync3 = None

# Test result structure
BenchResult = namedtuple(
    'BenchResult',
    ['test_name', 'duration', 'throughput_mb_s', 'files_per_sec', 'cpu_percent', 'memory_mb', 'network_mb_s', 'errors'],
)


class NetworkMonitor:
    """Monitor network usage during transfers"""

    def __init__(self, interface='eth0'):
        self.interface = interface
        self.monitoring = False
        self.samples = []

    def start(self):
        self.monitoring = True
        self.samples = []
        self.thread = threading.Thread(target=self._monitor)
        self.thread.start()

    def stop(self):
        self.monitoring = False
        if hasattr(self, 'thread'):
            self.thread.join()
        return self._calculate_average()

    def _monitor(self):
        last_bytes = psutil.net_io_counters().bytes_sent
        last_time = time.time()

        while self.monitoring:
            time.sleep(1)
            current_bytes = psutil.net_io_counters().bytes_sent
            current_time = time.time()

            bytes_diff = current_bytes - last_bytes
            time_diff = current_time - last_time

            if time_diff > 0:
                mb_per_sec = (bytes_diff / 1024 / 1024) / time_diff
                self.samples.append(mb_per_sec)

            last_bytes = current_bytes
            last_time = current_time

    def _calculate_average(self):
        return sum(self.samples) / len(self.samples) if self.samples else 0


class MSRSyncBenchmarker:
    """Comprehensive msrsync benchmarking suite"""

    def __init__(self, source_dir, dest_dir, msrsync_path='./msrsync3'):
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.msrsync_path = Path(msrsync_path)
        self.results = []

    def run_command(self, cmd, timeout=3600, verbose=True):
        """Execute command and measure performance"""
        if verbose:
            print(f"Running: {cmd}")

        # Start monitoring
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        net_monitor = NetworkMonitor()
        net_monitor.start()

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)

            end_time = time.time()
            duration = end_time - start_time

            # Stop monitoring
            network_mb_s = net_monitor.stop()
            end_cpu = psutil.cpu_percent()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024

            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'cpu_percent': (start_cpu + end_cpu) / 2,
                'memory_mb': end_memory - start_memory,
                'network_mb_s': network_mb_s,
            }

        except subprocess.TimeoutExpired:
            net_monitor.stop()
            return {'returncode': -1, 'error': 'timeout'}

    def create_test_data_parallel(self, num_files=1000, avg_size_kb=100, num_workers=None):
        """Create test dataset with parallel file generation - much faster!"""
        from functools import partial

        self.source_dir.mkdir(parents=True, exist_ok=True)

        # Auto-detect optimal worker count
        if num_workers is None:
            num_workers = min(os.cpu_count() * 2, 16)  # Cap at 16 to avoid overwhelming filesystem

        print(f"Creating {num_files} test files using {num_workers} workers...")

        # Create directory structure similar to typical NAS content
        dirs = ['photos', 'documents', 'videos', 'music', 'backups']
        for d in dirs:
            (self.source_dir / d).mkdir(parents=True, exist_ok=True)

        # Pre-generate random data in chunks to avoid repeated os.urandom() calls
        print("Pre-generating random data...")
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 50  # 50MB of random data pool
        random_data_pool = [os.urandom(chunk_size) for _ in range(num_chunks)]

        # Thread-safe counter for progress reporting
        progress_lock = threading.Lock()
        global_files_created = [0]  # Use list to make it mutable across threads

        def create_file_batch(file_range):
            """Create a batch of files - designed for parallel execution"""
            local_random = random.Random()  # Thread-local random instance
            local_random.seed(file_range[0])  # Deterministic but different per worker
            batch_count = 0

            for i in file_range:
                # Pick random directory
                subdir = local_random.choice(dirs)
                filename = f"file_{i:06d}.dat"
                filepath = self.source_dir / subdir / filename

                # Random file size (simulate real files)
                size = max(1, int(local_random.gauss(avg_size_kb * 1024, avg_size_kb * 512)))
                size = min(size, 1024 * 1024)  # Cap at 1MB for speed

                # Use pre-generated random data instead of calling os.urandom()
                data_needed = size
                file_data = b''

                while data_needed > 0:
                    chunk = local_random.choice(random_data_pool)
                    chunk_size_to_use = min(len(chunk), data_needed)
                    start_pos = local_random.randint(0, len(chunk) - chunk_size_to_use)
                    file_data += chunk[start_pos : start_pos + chunk_size_to_use]
                    data_needed -= chunk_size_to_use

                # Write file efficiently
                try:
                    filepath.write_bytes(file_data[:size])
                    batch_count += 1

                    # Thread-safe progress reporting every 100 files
                    if batch_count % 100 == 0:
                        with progress_lock:
                            global_files_created[0] += 100
                            print(f"\rCreated {global_files_created[0]} files...", end='', flush=True)

                except OSError as e:
                    print(f"Error creating {filepath}: {e}")
                    continue

            return batch_count

        # Split work into chunks for parallel processing
        chunk_size = max(1, num_files // num_workers)
        file_ranges = []

        for i in range(0, num_files, chunk_size):
            end = min(i + chunk_size, num_files)
            file_ranges.append(range(i, end))

        # Create files in parallel
        start_time = time.time()
        total_created = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_range = {executor.submit(create_file_batch, file_range): file_range for file_range in file_ranges}

            for future in concurrent.futures.as_completed(future_to_range):
                try:
                    batch_result = future.result()
                    total_created += batch_result
                except Exception as exc:
                    file_range = future_to_range[future]
                    print(f'File range {file_range} generated an exception: {exc}')

        elapsed = time.time() - start_time
        print()  # Newline after progress updates
        print(f"Test data created: {total_created} files in {elapsed:.1f}s ({total_created / elapsed:.0f} files/sec)")

    def create_test_data_ultra_fast(self, num_files=1000, avg_size_kb=100):
        """Ultra-fast file generation using minimal I/O"""
        self.source_dir.mkdir(parents=True, exist_ok=True)

        print(f"Creating {num_files} test files (ultra-fast mode)...")

        # Create directory structure
        dirs = ['photos', 'documents', 'videos', 'music', 'backups']
        for d in dirs:
            (self.source_dir / d).mkdir(parents=True, exist_ok=True)

        # Create files with minimal content but realistic sizes
        start_time = time.time()

        # Pre-generate a small random data template (reused for speed)
        template_data = os.urandom(4096)  # 4KB template

        for i in range(num_files):
            subdir = random.choice(dirs)
            filename = f"file_{i:06d}.dat"
            filepath = self.source_dir / subdir / filename

            # Random file size
            size = max(1, int(random.gauss(avg_size_kb * 1024, avg_size_kb * 512)))
            size = min(size, 1024 * 1024)  # Cap at 1MB

            try:
                # Fast file creation - write template data, then truncate to size
                if size <= len(template_data):
                    filepath.write_bytes(template_data[:size])
                else:
                    # Write template multiple times for larger files
                    full_writes = size // len(template_data)
                    remainder = size % len(template_data)

                    data = template_data * full_writes
                    if remainder:
                        data += template_data[:remainder]
                    filepath.write_bytes(data)

            except OSError as e:
                print(f"Error creating {filepath}: {e}")
                continue

            if (i + 1) % 1000 == 0:
                print(f"\rCreated {i + 1} files...", end='', flush=True)

        elapsed = time.time() - start_time
        print()  # Newline after progress updates
        print(f"Test data created: {num_files} files in {elapsed:.1f}s ({num_files / elapsed:.0f} files/sec)")

    def create_test_data_touch_only(self, num_files=1000):
        """Fastest option: create empty files (for crawl testing only)"""
        self.source_dir.mkdir(parents=True, exist_ok=True)

        print(f"Creating {num_files} empty test files (touch mode)...")

        # Create directory structure
        dirs = ['photos', 'documents', 'videos', 'music', 'backups']
        for d in dirs:
            (self.source_dir / d).mkdir(parents=True, exist_ok=True)

        start_time = time.time()

        def touch_file_batch(file_range):
            local_random = random.Random(file_range[0])  # Thread-local seeded random
            for i in file_range:
                subdir = local_random.choice(dirs)
                filename = f"file_{i:06d}.dat"
                filepath = self.source_dir / subdir / filename

                try:
                    # Touch file (create empty)
                    filepath.touch()
                except OSError:
                    continue
            return len(file_range)

        # Split into batches
        num_workers = min(os.cpu_count() * 2, 16)
        chunk_size = max(1, num_files // num_workers)
        file_ranges = [range(i, min(i + chunk_size, num_files)) for i in range(0, num_files, chunk_size)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(touch_file_batch, file_range) for file_range in file_ranges]
            total_created = sum(future.result() for future in concurrent.futures.as_completed(futures))

        elapsed = time.time() - start_time
        print()  # Newline after progress updates
        print(f"Test data created: {total_created} files in {elapsed:.1f}s ({total_created / elapsed:.0f} files/sec)")

    def create_test_data(self, num_files=1000, avg_size_kb=100):
        """Original test data creation (kept for compatibility)"""
        self.source_dir.mkdir(parents=True, exist_ok=True)

        print(f"Creating {num_files} test files...")

        # Create directory structure similar to typical NAS content
        dirs = ['photos', 'documents', 'videos', 'music', 'backups']
        for d in dirs:
            (self.source_dir / d).mkdir(parents=True, exist_ok=True)

        file_count = 0

        for i in range(num_files):
            # Pick random directory
            subdir = random.choice(dirs)
            filename = f"file_{i:06d}.dat"
            filepath = self.source_dir / subdir / filename

            # Random file size (simulate real files)
            size = max(1, int(random.gauss(avg_size_kb * 1024, avg_size_kb * 512)))

            try:
                filepath.write_bytes(os.urandom(min(size, 1024 * 1024)))  # Cap at 1MB for speed
            except OSError as e:
                print(f"Error creating {filepath}: {e}")
                continue

            file_count += 1
            if file_count % 100 == 0:
                print(f"\rCreated {file_count} files...", end='', flush=True)

        print()  # Newline after progress updates
        print(f"Test data created: {file_count} files")

    def benchmark_crawl_methods(self):
        """Compare fd vs os.walk crawling performance"""
        print("\n=== Crawling Method Comparison ===")

        # Test fd crawling
        if shutil.which('fd'):
            print("Testing fd (modern file finder)...")
            cmd = f"fd --type f . {self.source_dir} > /dev/null 2>&1"
            result = self.run_command(cmd, verbose=False)
            if result['returncode'] == 0:
                self.results.append(
                    BenchResult('fd_crawl', result['duration'], 0, 0, result['cpu_percent'], result['memory_mb'], 0, 0)
                )
                print(f"  fd: {result['duration']:.3f}s")

        # Test find crawling
        print("Testing find (traditional Unix tool)...")
        cmd = f"find {self.source_dir} -type f > /dev/null 2>&1"
        result = self.run_command(cmd, verbose=False)
        if result['returncode'] == 0:
            self.results.append(
                BenchResult('find_crawl', result['duration'], 0, 0, result['cpu_percent'], result['memory_mb'], 0, 0)
            )
            print(f"  find: {result['duration']:.3f}s")

        # Test Python pathlib crawling
        print("Testing Python pathlib (modern Python approach)...")
        start_time = time.time()
        try:
            file_count = 0
            for filepath in Path(self.source_dir).rglob('*'):
                if filepath.is_file():
                    file_count += 1
                    filepath.stat()
            duration = time.time() - start_time
            self.results.append(
                BenchResult('python_pathlib_crawl', duration, 0, 0, 0, 0, 0, 0)
            )
            print(f"  pathlib: {duration:.3f}s ({file_count} files)")
        except Exception as e:
            print(f"  pathlib: failed ({e})")

        # Test Python os.walk crawling (for comparison)
        print("Testing Python os.walk (traditional Python approach)...")
        start_time = time.time()
        try:
            file_count = 0
            for root, _dirs, files in os.walk(self.source_dir):
                for f in files:
                    file_count += 1
                    os.lstat(os.path.join(root, f))
            duration = time.time() - start_time
            self.results.append(
                BenchResult('python_walk_crawl', duration, 0, 0, 0, 0, 0, 0)
            )
            print(f"  os.walk: {duration:.3f}s ({file_count} files)")
        except Exception as e:
            print(f"  os.walk: failed ({e})")

    def benchmark_compression_levels(self):
        """Test different compression levels for network optimization"""
        print("\n=== Compression Level Testing ===")

        compression_levels = [0, 1, 3]

        for level in compression_levels:
            dest_test = self.dest_dir / f'compress_test_{level}'
            if dest_test.exists():
                shutil.rmtree(dest_test)

            compress_opt = f"--compress-level={level}" if level > 0 else ""
            cmd = f"rsync -aS --numeric-ids {compress_opt} {self.source_dir}/ {dest_test}/"

            result = self.run_command(cmd)
            if result['returncode'] == 0:
                # Calculate throughput
                total_size = self._get_directory_size(self.source_dir)
                throughput = (total_size / 1024 / 1024) / result['duration']

                self.results.append(
                    BenchResult(
                        f'compression_level_{level}',
                        result['duration'],
                        throughput,
                        0,
                        result['cpu_percent'],
                        result['memory_mb'],
                        result['network_mb_s'],
                        0,
                    )
                )

                print(f"Compression {level}: {result['duration']:.1f}s, {throughput:.1f} MB/s, CPU: {result['cpu_percent']:.1f}%")

    def benchmark_process_scaling(self):
        """Test msrsync process scaling with network bottleneck"""
        print("\n=== Process Scaling Analysis ===")

        process_counts = [1, 2, 4]  # Reduced from [1, 2, 3, 4, 6, 8]
        bucket_configs = [
            ('4G', 8000),  # Only test medium buckets to save time
        ]

        for size, files in bucket_configs:
            print(f"\nTesting bucket config: {size}, {files} files")

            for procs in process_counts:
                dest_test = self.dest_dir / f'proc_test_{procs}_{size}'
                if dest_test.exists():
                    shutil.rmtree(dest_test)

                cmd = (
                    f"{self.msrsync_path} --exclude-caches -p {procs} "
                    f"-s {size} -f {files} "
                    f"--rsync '-aS --numeric-ids --inplace --compress-level=3' "
                    f"{self.source_dir}/ {dest_test}/"
                )

                result = self.run_command(cmd)
                if result['returncode'] == 0:
                    total_size = self._get_directory_size(self.source_dir)
                    file_count = self._count_files(self.source_dir)
                    throughput = (total_size / 1024 / 1024) / result['duration']
                    files_per_sec = file_count / result['duration']

                    self.results.append(
                        BenchResult(
                            f'procs_{procs}_{size}_{files}',
                            result['duration'],
                            throughput,
                            files_per_sec,
                            result['cpu_percent'],
                            result['memory_mb'],
                            result['network_mb_s'],
                            0,
                        )
                    )

                    print(f"  {procs} processes: {result['duration']:.1f}s, {throughput:.1f} MB/s, {files_per_sec:.0f} files/s")

                    # Stop scaling if no improvement (network saturated) - more aggressive
                    if len(self.results) >= 2:
                        proc_results = [r for r in self.results if r.test_name.startswith('procs_') and size in r.test_name]
                        if len(proc_results) >= 2:
                            last_two = proc_results[-2:]
                            improvement = (last_two[1].throughput_mb_s - last_two[0].throughput_mb_s) / last_two[0].throughput_mb_s
                            if improvement < 0.05:  # Less than 5% improvement (more aggressive)
                                print(f"    Performance plateau detected at {procs} processes (improvement: {improvement:.1%})")
                                break

    def benchmark_network_patterns(self):
        """Test different network usage patterns"""
        print("\n=== Network Pattern Analysis ===")

        patterns = [
            # (name, rsync_opts, description)
            ('baseline', '-aS --numeric-ids', 'Baseline transfer'),
            ('compressed', '-aS --numeric-ids --compress-level=3', 'With compression'),
            ('inplace', '-aS --numeric-ids --inplace', 'Inplace updates'),
            ('optimized', '-aS --numeric-ids --inplace --compress-level=3', 'Full optimization'),
        ]

        for name, opts, desc in patterns:
            dest_test = self.dest_dir / f'pattern_{name}'
            if dest_test.exists():
                shutil.rmtree(dest_test)

            cmd = f"rsync {opts} {self.source_dir}/ {dest_test}/"

            result = self.run_command(cmd)
            if result['returncode'] == 0:
                total_size = self._get_directory_size(self.source_dir)
                throughput = (total_size / 1024 / 1024) / result['duration']

                self.results.append(
                    BenchResult(
                        f'pattern_{name}',
                        result['duration'],
                        throughput,
                        0,
                        result['cpu_percent'],
                        result['memory_mb'],
                        result['network_mb_s'],
                        0,
                    )
                )

                print(f"{desc}: {result['duration']:.1f}s, {throughput:.1f} MB/s")

    def benchmark_memory_usage(self):
        """Test memory usage patterns with different configurations"""
        print("\n=== Memory Usage Analysis ===")

        configs = [
            ('medium_buckets', '-p 2 -s 4G -f 5000'),  # Reduced from 4 configs to 1 for speed
        ]

        for name, opts in configs:
            dest_test = self.dest_dir / f'memory_{name}'
            if dest_test.exists():
                shutil.rmtree(dest_test)

            cmd = f"{self.msrsync_path} {opts} --dry-run {self.source_dir}/ {dest_test}/"

            result = self.run_command(cmd)
            if result['returncode'] == 0:
                self.results.append(
                    BenchResult(f'memory_{name}', result['duration'], 0, 0, result['cpu_percent'], result['memory_mb'], 0, 0)
                )

                print(f"{name}: {result['memory_mb']:.1f} MB peak memory")

    def _get_directory_size(self, path):
        """Calculate total directory size in bytes using pathlib"""
        total = 0
        path = Path(path)
        for filepath in path.rglob('*'):
            if filepath.is_file():
                with contextlib.suppress(OSError):
                    total += filepath.stat().st_size
        return total

    def _count_files(self, path):
        """Count total files in directory using pathlib"""
        path = Path(path)
        return sum(1 for filepath in path.rglob('*') if filepath.is_file())

    def generate_report(self):
        """Generate comprehensive benchmark report"""
        print("\n" + "=" * 60)
        print("MSRSYNC NETWORK-AWARE BENCHMARK REPORT")
        print("=" * 60)

        # Group results by test type
        by_category = defaultdict(list)
        for result in self.results:
            category = result.test_name.split('_')[0]
            by_category[category].append(result)

        # System info
        print("\nSystem Information:")
        print(f"CPU cores: {psutil.cpu_count()}")
        print(f"RAM: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
        print(
            f"Test data: {self._count_files(self.source_dir)} files, "
            f"{self._get_directory_size(self.source_dir) / 1024 / 1024:.1f} MB"
        )

        # Crawling comparison
        crawl_categories = ['fd', 'find', 'python']
        crawl_results = []
        for cat in crawl_categories:
            if cat in by_category:
                crawl_results.extend(by_category[cat])

        if crawl_results:
            print("\nDirectory Crawling Performance:")
            for result in sorted(crawl_results, key=lambda x: x.duration):
                print(f"  {result.test_name}: {result.duration:.3f}s")

        # Compression analysis
        if 'compression' in by_category:
            print("\nCompression Level Analysis:")
            comp_results = sorted(by_category['compression'], key=lambda x: int(x.test_name.split('_')[-1]))
            print(f"{'Level':<8} {'Time':<8} {'Throughput':<12} {'CPU %':<8} {'Network':<10}")
            print("-" * 50)

            for result in comp_results:
                level = result.test_name.split('_')[-1]
                print(
                    f"{level:<8} {result.duration:<8.1f} "
                    f"{result.throughput_mb_s:<12.1f} {result.cpu_percent:<8.1f} "
                    f"{result.network_mb_s:<10.1f}"
                )

        # Process scaling
        if 'procs' in by_category:
            print("\nProcess Scaling Analysis:")
            proc_results = by_category['procs']

            # Group by bucket config
            bucket_groups = defaultdict(list)
            for result in proc_results:
                parts = result.test_name.split('_')
                bucket_key = f"{parts[2]}_{parts[3]}"
                bucket_groups[bucket_key].append(result)

            for bucket_config, results in bucket_groups.items():
                print(f"\n  Bucket config: {bucket_config}")
                print(f"  {'Processes':<10} {'Time':<8} {'Throughput':<12} {'Files/s':<10}")
                print("  " + "-" * 42)

                for result in sorted(results, key=lambda x: int(x.test_name.split('_')[1])):
                    procs = result.test_name.split('_')[1]
                    print(f"  {procs:<10} {result.duration:<8.1f} {result.throughput_mb_s:<12.1f} {result.files_per_sec:<10.0f}")

        # Network patterns
        if 'pattern' in by_category:
            print("\nNetwork Pattern Comparison:")
            print(f"{'Pattern':<15} {'Time':<8} {'Throughput':<12} {'Network':<10}")
            print("-" * 47)

            for result in sorted(by_category['pattern'], key=lambda x: x.throughput_mb_s, reverse=True):
                pattern = result.test_name.replace('pattern_', '')
                print(f"{pattern:<15} {result.duration:<8.1f} {result.throughput_mb_s:<12.1f} {result.network_mb_s:<10.1f}")

        # Recommendations
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS FOR YOUR SETUP")
        print("=" * 60)

        self._generate_recommendations()

    def _generate_recommendations(self):
        """Generate specific recommendations based on results"""
        print("\nBased on your test results:")

        # Find best compression level
        comp_results = [r for r in self.results if 'compression' in r.test_name]
        if comp_results:
            best_comp = max(comp_results, key=lambda x: x.throughput_mb_s)
            level = best_comp.test_name.split('_')[-1]
            print(f"✓ Use compression level {level} ({best_comp.throughput_mb_s:.1f} MB/s)")

        # Find optimal process count
        proc_results = [r for r in self.results if 'procs' in r.test_name]
        if proc_results:
            best_procs = max(proc_results, key=lambda x: x.throughput_mb_s)
            procs = best_procs.test_name.split('_')[1]
            bucket_size = best_procs.test_name.split('_')[2]
            print(f"✓ Use {procs} processes with {bucket_size} buckets ({best_procs.throughput_mb_s:.1f} MB/s)")

        # Crawling method recommendations
        crawl_results = [r for r in self.results if 'crawl' in r.test_name]
        if len(crawl_results) > 1:
            fastest_crawl = min(crawl_results, key=lambda x: x.duration)
            print(f"✓ Fastest directory crawling: {fastest_crawl.test_name} ({fastest_crawl.duration:.3f}s)")

        # Network saturation check
        network_speeds = [r.network_mb_s for r in self.results if r.network_mb_s > 0]
        if network_speeds:
            avg_network = sum(network_speeds) / len(network_speeds)
            if avg_network > 100:
                print(f"⚠ Network appears saturated (~{avg_network:.0f} MB/s)")
                print("  Consider: More compression, fewer processes")
            else:
                print(f"ℹ Network not saturated (~{avg_network:.0f} MB/s)")
                print("  Consider: More processes, less compression")


def main():
    parser = argparse.ArgumentParser(description='msrsync network-aware benchmarks')
    parser.add_argument('--source', required=True, help='Source directory')
    parser.add_argument('--dest', required=True, help='Destination directory')
    parser.add_argument('--msrsync', default='./msrsync3', help='Path to msrsync')
    parser.add_argument('--create-data', type=int, help='Create test data (number of files)')
    parser.add_argument(
        '--file-mode',
        choices=['realistic', 'fast', 'touch'],
        default='fast',
        help='File creation mode: realistic (slow, real sizes), fast (parallel), touch (empty files)',
    )
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')

    args = parser.parse_args()

    # Ensure directories exist using pathlib
    Path(args.source).mkdir(parents=True, exist_ok=True)
    Path(args.dest).mkdir(parents=True, exist_ok=True)

    benchmarker = MSRSyncBenchmarker(args.source, args.dest, args.msrsync)

    # Create test data if requested with chosen method
    if args.create_data:
        if args.file_mode == 'realistic':
            benchmarker.create_test_data(args.create_data)  # Original slow method
        elif args.file_mode == 'fast':
            benchmarker.create_test_data_parallel(args.create_data)  # Parallel method
        elif args.file_mode == 'touch':
            benchmarker.create_test_data_touch_only(args.create_data)  # Touch only

    # Run benchmark suite
    print("Starting network-aware msrsync benchmarks...")

    benchmarker.benchmark_crawl_methods()

    if not args.quick:
        benchmarker.benchmark_compression_levels()
        benchmarker.benchmark_process_scaling()
        benchmarker.benchmark_network_patterns()
        benchmarker.benchmark_memory_usage()
    else:
        print("Quick mode: testing basic compression and 2-4 processes only")
        # Quick compression test
        for level in [0, 3]:
            dest_test = benchmarker.dest_dir / f'quick_compress_{level}'
            compress_opt = f"--compress-level={level}" if level > 0 else ""
            cmd = f"rsync -aS --numeric-ids {compress_opt} {benchmarker.source_dir}/ {dest_test}/"
            result = benchmarker.run_command(cmd)

        # Quick process test
        for procs in [2, 3, 4]:
            dest_test = benchmarker.dest_dir / f'quick_proc_{procs}'
            cmd = (
                f"{benchmarker.msrsync_path} -p {procs} -s 4G "
                f"--rsync '-aS --numeric-ids --compress-level=3' "
                f"{benchmarker.source_dir}/ {dest_test}/"
            )
            result = benchmarker.run_command(cmd)

    benchmarker.generate_report()

    # Save results to JSON
    results_file = Path('benchmark_results.json')
    with results_file.open('w') as f:
        json.dump([r._asdict() for r in benchmarker.results], f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")


if __name__ == '__main__':
    main()
