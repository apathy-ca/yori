#!/bin/bash
#
# YORI Load Test Runner
#
# This script runs all load tests, soak tests, and chaos tests.
#
# Usage:
#   ./run_load_tests.sh [quick|load|soak|chaos|all]
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROXY_PORT=8080
PROXY_HOST="http://localhost:${PROXY_PORT}"
PROXY_PID=""

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to start YORI proxy
start_proxy() {
    print_info "Starting YORI proxy on port ${PROXY_PORT}..."

    if [ -f "yori.conf.example" ]; then
        python -m yori --config yori.conf.example --port ${PROXY_PORT} > /tmp/yori_test.log 2>&1 &
    else
        python -m yori --port ${PROXY_PORT} > /tmp/yori_test.log 2>&1 &
    fi

    PROXY_PID=$!
    print_info "Proxy started with PID: ${PROXY_PID}"

    # Wait for proxy to be ready
    print_info "Waiting for proxy to be ready..."
    for i in {1..30}; do
        if curl -s "${PROXY_HOST}/health" > /dev/null 2>&1; then
            print_info "Proxy is ready!"
            return 0
        fi
        sleep 1
    done

    print_error "Proxy failed to start within 30 seconds"
    cat /tmp/yori_test.log
    return 1
}

# Function to stop YORI proxy
stop_proxy() {
    if [ -n "${PROXY_PID}" ]; then
        print_info "Stopping YORI proxy (PID: ${PROXY_PID})..."
        kill ${PROXY_PID} 2>/dev/null || true
        wait ${PROXY_PID} 2>/dev/null || true
        print_info "Proxy stopped"
    fi
}

# Cleanup on exit
cleanup() {
    stop_proxy
}

trap cleanup EXIT

# Function to run load tests
run_load_tests() {
    print_info "=== Running Load Tests ==="

    # Quick test (100 users)
    print_info "Test 1: 100 concurrent users (5 minutes)"
    locust -f tests/load/locustfile.py \
        --headless \
        --users 100 \
        --spawn-rate 10 \
        --run-time 5m \
        --host ${PROXY_HOST} \
        --html tests/load/report_100_users.html \
        --csv tests/load/results_100_users

    # High load test (1000 users) - if requested
    if [ "$1" == "full" ]; then
        print_info "Test 2: 1000 concurrent users (15 minutes)"
        locust -f tests/load/locustfile.py \
            --headless \
            --users 1000 \
            --spawn-rate 50 \
            --run-time 15m \
            --host ${PROXY_HOST} \
            --html tests/load/report_1000_users.html \
            --csv tests/load/results_1000_users
    fi

    print_info "Load tests complete! Reports saved to tests/load/"
}

# Function to run quick soak test
run_soak_tests() {
    print_info "=== Running Soak Test ==="

    if [ "$1" == "quick" ]; then
        print_info "Running quick 5-minute soak test..."
        python tests/soak/soak_test.py --quick-test
    else
        print_info "Running full 24-hour soak test..."
        print_warn "This will take 24 hours. Press Ctrl+C to stop."
        python tests/soak/soak_test.py
    fi

    print_info "Soak test complete! Results saved to tests/soak/"
}

# Function to run chaos tests
run_chaos_tests() {
    print_info "=== Running Chaos Tests ==="

    # Stop existing proxy if running
    stop_proxy

    # Start fresh proxy for chaos tests
    start_proxy

    python tests/chaos/chaos_test.py --url ${PROXY_HOST}

    print_info "Chaos tests complete!"
}

# Function to run quick validation
run_quick_tests() {
    print_info "=== Running Quick Validation Tests ==="

    # Quick load test (1 minute)
    print_info "Quick load test (1 minute, 50 users)..."
    locust -f tests/load/locustfile.py \
        --headless \
        --users 50 \
        --spawn-rate 10 \
        --run-time 1m \
        --host ${PROXY_HOST} \
        --html tests/load/report_quick.html

    # Quick soak test (5 minutes)
    print_info "Quick soak test (5 minutes)..."
    python tests/soak/soak_test.py --quick-test

    print_info "Quick tests complete!"
}

# Main script
main() {
    TEST_TYPE=${1:-quick}

    print_info "YORI Load Test Runner"
    print_info "Test type: ${TEST_TYPE}"
    echo

    # Check dependencies
    if ! command -v locust &> /dev/null; then
        print_error "Locust is not installed. Run: pip install locust"
        exit 1
    fi

    # Start proxy
    start_proxy

    # Run tests based on argument
    case ${TEST_TYPE} in
        quick)
            run_quick_tests
            ;;
        load)
            run_load_tests
            ;;
        load-full)
            run_load_tests full
            ;;
        soak)
            run_soak_tests quick
            ;;
        soak-full)
            run_soak_tests full
            ;;
        chaos)
            run_chaos_tests
            ;;
        all)
            run_quick_tests
            run_chaos_tests
            ;;
        *)
            print_error "Unknown test type: ${TEST_TYPE}"
            echo "Usage: $0 [quick|load|load-full|soak|soak-full|chaos|all]"
            echo
            echo "Test types:"
            echo "  quick      - Quick validation (5 minutes)"
            echo "  load       - Load test with 100 users (5 minutes)"
            echo "  load-full  - Load tests with 100 and 1000 users (20 minutes)"
            echo "  soak       - Quick soak test (5 minutes)"
            echo "  soak-full  - Full 24-hour soak test"
            echo "  chaos      - Chaos engineering tests (10 minutes)"
            echo "  all        - Quick + chaos tests (15 minutes)"
            exit 1
            ;;
    esac

    print_info "All tests completed successfully!"
}

main "$@"
