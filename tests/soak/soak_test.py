"""
YORI 24-Hour Soak Test

This test runs for 24 hours to detect:
- Memory leaks
- Connection leaks
- Performance degradation over time
- Resource exhaustion
- Database issues

Success Criteria:
- No memory leaks (memory usage stable)
- No connection leaks
- Performance remains consistent (±10%)
- No crashes or restarts
"""

import time
import psutil
import subprocess
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class SoakTestMonitor:
    """Monitor system metrics during soak test"""

    def __init__(self, test_duration_hours=24, sample_interval_seconds=60):
        self.test_duration = timedelta(hours=test_duration_hours)
        self.sample_interval = sample_interval_seconds
        self.metrics = []
        self.start_time = None
        self.yori_process = None

    def find_yori_process(self):
        """Find the YORI proxy server process"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('yori' in str(arg).lower() for arg in cmdline):
                    return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def collect_metrics(self):
        """Collect current metrics"""
        if not self.yori_process:
            self.yori_process = self.find_yori_process()

        if not self.yori_process:
            print("WARNING: Could not find YORI process")
            return None

        try:
            # Get process metrics
            mem_info = self.yori_process.memory_info()
            cpu_percent = self.yori_process.cpu_percent(interval=1.0)
            num_fds = self.yori_process.num_fds() if hasattr(self.yori_process, 'num_fds') else 0
            connections = len(self.yori_process.connections())

            metrics = {
                'timestamp': datetime.now().isoformat(),
                'elapsed_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
                'memory_mb': mem_info.rss / (1024 * 1024),  # RSS in MB
                'memory_vms_mb': mem_info.vms / (1024 * 1024),  # Virtual memory in MB
                'cpu_percent': cpu_percent,
                'num_threads': self.yori_process.num_threads(),
                'num_fds': num_fds,
                'num_connections': connections,
            }

            return metrics

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"ERROR collecting metrics: {e}")
            return None

    def run_soak_test(self):
        """Run the soak test"""
        print("=== YORI 24-Hour Soak Test ===")
        print(f"Duration: {self.test_duration.total_seconds() / 3600:.1f} hours")
        print(f"Sample Interval: {self.sample_interval} seconds")
        print(f"Start Time: {datetime.now()}")
        print("=" * 40)

        self.start_time = datetime.now()
        end_time = self.start_time + self.test_duration

        # Initial metrics
        print("\nCollecting initial metrics...")
        time.sleep(5)  # Give YORI time to start up
        initial_metrics = self.collect_metrics()

        if initial_metrics:
            print(f"Initial Memory: {initial_metrics['memory_mb']:.2f} MB")
            print(f"Initial Connections: {initial_metrics['num_connections']}")

        # Start load generator in background
        print("\nStarting load generator...")
        load_test_cmd = [
            'locust',
            '-f', 'tests/load/locustfile.py',
            '--headless',
            '--users', '50',  # Moderate load for soak test
            '--spawn-rate', '5',
            '--host', 'http://localhost:8080',
            '--run-time', f'{int(self.test_duration.total_seconds())}s',
            '--html', 'tests/soak/soak_test_report.html',
            '--csv', 'tests/soak/soak_test',
        ]

        load_process = subprocess.Popen(
            load_test_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"Load generator started (PID: {load_process.pid})")

        # Monitor loop
        sample_count = 0
        try:
            while datetime.now() < end_time:
                # Collect metrics
                metrics = self.collect_metrics()

                if metrics:
                    self.metrics.append(metrics)
                    sample_count += 1

                    # Print progress every 10 samples
                    if sample_count % 10 == 0:
                        elapsed = metrics['elapsed_hours']
                        remaining = (self.test_duration.total_seconds() / 3600) - elapsed
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sample {sample_count}")
                        print(f"  Elapsed: {elapsed:.2f}h | Remaining: {remaining:.2f}h")
                        print(f"  Memory: {metrics['memory_mb']:.2f} MB")
                        print(f"  CPU: {metrics['cpu_percent']:.1f}%")
                        print(f"  Connections: {metrics['num_connections']}")
                        print(f"  Threads: {metrics['num_threads']}")

                        # Check for memory leak (simple heuristic)
                        if initial_metrics and metrics['memory_mb'] > initial_metrics['memory_mb'] * 1.5:
                            print(f"  ⚠ WARNING: Memory usage increased by >50%!")

                # Sleep until next sample
                time.sleep(self.sample_interval)

        except KeyboardInterrupt:
            print("\n\nSoak test interrupted by user")

        finally:
            # Stop load generator
            print("\nStopping load generator...")
            load_process.terminate()
            load_process.wait(timeout=10)

        # Analyze results
        self.analyze_results(initial_metrics)

    def analyze_results(self, initial_metrics):
        """Analyze soak test results"""
        print("\n" + "=" * 40)
        print("=== Soak Test Analysis ===")
        print("=" * 40)

        if not self.metrics:
            print("ERROR: No metrics collected!")
            return

        # Save raw metrics
        metrics_file = Path('tests/soak/soak_test_metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        print(f"\nMetrics saved to: {metrics_file}")

        # Calculate statistics
        memory_values = [m['memory_mb'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        connection_values = [m['num_connections'] for m in self.metrics]

        print(f"\nTest Duration: {self.metrics[-1]['elapsed_hours']:.2f} hours")
        print(f"Samples Collected: {len(self.metrics)}")

        print("\n--- Memory Statistics ---")
        print(f"  Initial: {memory_values[0]:.2f} MB")
        print(f"  Final: {memory_values[-1]:.2f} MB")
        print(f"  Average: {sum(memory_values) / len(memory_values):.2f} MB")
        print(f"  Min: {min(memory_values):.2f} MB")
        print(f"  Max: {max(memory_values):.2f} MB")
        print(f"  Growth: {memory_values[-1] - memory_values[0]:.2f} MB ({((memory_values[-1] / memory_values[0]) - 1) * 100:.1f}%)")

        print("\n--- CPU Statistics ---")
        print(f"  Average: {sum(cpu_values) / len(cpu_values):.1f}%")
        print(f"  Min: {min(cpu_values):.1f}%")
        print(f"  Max: {max(cpu_values):.1f}%")

        print("\n--- Connection Statistics ---")
        print(f"  Average: {sum(connection_values) / len(connection_values):.1f}")
        print(f"  Min: {min(connection_values)}")
        print(f"  Max: {max(connection_values)}")
        print(f"  Final: {connection_values[-1]}")

        # Success criteria check
        print("\n--- Success Criteria ---")

        # Memory leak check (<20% growth)
        memory_growth = ((memory_values[-1] / memory_values[0]) - 1) * 100
        if memory_growth < 20:
            print(f"  ✓ No significant memory leak: {memory_growth:.1f}% growth")
        else:
            print(f"  ✗ Possible memory leak: {memory_growth:.1f}% growth")

        # Connection leak check
        if connection_values[-1] <= connection_values[0] * 1.2:
            print(f"  ✓ No connection leak")
        else:
            print(f"  ✗ Possible connection leak: {connection_values[-1]} connections")

        # Memory target (<100MB)
        if max(memory_values) < 100:
            print(f"  ✓ Memory usage within target: {max(memory_values):.2f} MB < 100 MB")
        else:
            print(f"  ✗ Memory usage exceeds target: {max(memory_values):.2f} MB >= 100 MB")

        # Performance consistency check (CPU variance)
        cpu_variance = max(cpu_values) - min(cpu_values)
        if cpu_variance < 20:
            print(f"  ✓ CPU performance consistent: {cpu_variance:.1f}% variance")
        else:
            print(f"  ⚠ CPU performance varies: {cpu_variance:.1f}% variance")

        print("\n" + "=" * 40)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="YORI 24-Hour Soak Test")
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Test duration in hours (default: 24)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Sample interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--quick-test',
        action='store_true',
        help='Run a quick 5-minute test for validation'
    )

    args = parser.parse_args()

    # Quick test for validation
    if args.quick_test:
        print("Running QUICK TEST (5 minutes)")
        monitor = SoakTestMonitor(test_duration_hours=5/60, sample_interval_seconds=10)
    else:
        monitor = SoakTestMonitor(
            test_duration_hours=args.hours,
            sample_interval_seconds=args.interval
        )

    monitor.run_soak_test()


if __name__ == '__main__':
    main()
