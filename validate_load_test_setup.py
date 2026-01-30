#!/usr/bin/env python3
"""
YORI Load Test Setup Validation

This script validates that the load testing infrastructure is properly set up:
1. Dependencies are installed
2. YORI proxy can start
3. Health endpoint is accessible
4. Locust can run basic tests
"""

import subprocess
import sys
import time
import requests
from pathlib import Path


def print_status(message, success=None):
    """Print status message with color"""
    if success is None:
        print(f"[....] {message}")
    elif success:
        print(f"[✓] {message}")
    else:
        print(f"[✗] {message}")


def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n=== Checking Dependencies ===")

    dependencies = {
        'locust': 'Locust load testing framework',
        'psutil': 'Process monitoring',
        'requests': 'HTTP client library',
    }

    all_ok = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print_status(f"{description} ({module})", success=True)
        except ImportError:
            print_status(f"{description} ({module}) - NOT INSTALLED", success=False)
            all_ok = False

    return all_ok


def check_test_files():
    """Check if test files exist"""
    print("\n=== Checking Test Files ===")

    test_files = [
        ('tests/load/locustfile.py', 'Locust load test scenarios'),
        ('tests/soak/soak_test.py', 'Soak test (24-hour)'),
        ('tests/chaos/chaos_test.py', 'Chaos engineering tests'),
        ('run_load_tests.sh', 'Test runner script'),
    ]

    all_ok = True
    for filepath, description in test_files:
        path = Path(filepath)
        if path.exists():
            print_status(f"{description} - {filepath}", success=True)
        else:
            print_status(f"{description} - {filepath} - NOT FOUND", success=False)
            all_ok = False

    return all_ok


def start_proxy(port=8080):
    """Start YORI proxy server"""
    print(f"\n=== Starting YORI Proxy (port {port}) ===")

    # Check if config exists
    config_file = Path('yori_test.conf')
    if not config_file.exists():
        print_status("Test config file not found", success=False)
        return None

    # Start proxy
    cmd = [
        sys.executable, '-m', 'yori',
        '--config', str(config_file),
        '--port', str(port),
        '--no-tls'
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for startup
        print_status("Waiting for proxy to start...", success=None)
        time.sleep(3)

        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print_status("Proxy failed to start", success=False)
            print("STDOUT:", stdout[:500])
            print("STDERR:", stderr[:500])
            return None

        print_status("Proxy started successfully", success=True)
        return process

    except Exception as e:
        print_status(f"Failed to start proxy: {e}", success=False)
        return None


def test_health_endpoint(port=8080):
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")

    url = f"http://localhost:{port}/health"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print_status(f"Health check OK: {data}", success=True)

            # Validate response structure
            if 'status' in data and data['status'] == 'healthy':
                print_status("Health response format valid", success=True)
                return True
            else:
                print_status("Health response format invalid", success=False)
                return False
        else:
            print_status(f"Health check failed with status {response.status_code}", success=False)
            return False

    except Exception as e:
        print_status(f"Health check error: {e}", success=False)
        return False


def run_quick_load_test(port=8080):
    """Run a quick Locust load test"""
    print("\n=== Running Quick Load Test ===")

    cmd = [
        'locust',
        '-f', 'tests/load/locustfile.py',
        '--headless',
        '--users', '5',
        '--spawn-rate', '1',
        '--run-time', '5s',
        '--host', f'http://localhost:{port}'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Check for success in output
        if 'test_start' in result.stdout.lower() or result.returncode == 0:
            print_status("Quick load test completed", success=True)
            # Print last 10 lines of output
            lines = result.stdout.split('\n')
            for line in lines[-10:]:
                if line.strip():
                    print(f"  {line}")
            return True
        else:
            print_status("Load test failed", success=False)
            print("Output:", result.stdout[-500:])
            print("Errors:", result.stderr[-500:])
            return False

    except subprocess.TimeoutExpired:
        print_status("Load test timed out", success=False)
        return False
    except Exception as e:
        print_status(f"Load test error: {e}", success=False)
        return False


def main():
    """Main validation routine"""
    print("=" * 60)
    print("YORI Load Test Setup Validation")
    print("=" * 60)

    results = {}

    # Check dependencies
    results['dependencies'] = check_dependencies()

    # Check test files
    results['test_files'] = check_test_files()

    # Only proceed if basic checks pass
    if not all([results['dependencies'], results['test_files']]):
        print("\n" + "=" * 60)
        print("Validation FAILED: Fix missing dependencies or files")
        print("=" * 60)
        return False

    # Start proxy
    proxy_process = start_proxy()
    if not proxy_process:
        print("\n" + "=" * 60)
        print("Validation FAILED: Could not start proxy")
        print("=" * 60)
        return False

    try:
        # Test health endpoint
        results['health'] = test_health_endpoint()

        # Run quick load test
        if results['health']:
            results['load_test'] = run_quick_load_test()
        else:
            results['load_test'] = False

    finally:
        # Stop proxy
        print("\n=== Stopping Proxy ===")
        proxy_process.terminate()
        try:
            proxy_process.wait(timeout=5)
            print_status("Proxy stopped", success=True)
        except subprocess.TimeoutExpired:
            proxy_process.kill()
            print_status("Proxy killed (did not stop gracefully)", success=False)

    # Print summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{test:20} {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Ready for load testing!")
    else:
        print("✗ SOME CHECKS FAILED - Review output above")
    print("=" * 60)

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
