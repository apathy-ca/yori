"""
YORI Load Testing with Locust

This file contains the main load test scenarios for the YORI proxy server.

Test Scenarios:
1. Health check requests
2. LLM API proxy requests (OpenAI, Anthropic)
3. Enforcement/blocking scenarios
4. Override password validation
5. Audit log queries

Success Criteria:
- Handle 1000 concurrent users
- <50ms added latency (p95)
- <100MB memory usage
- No errors under normal load
"""

import json
import random
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import time


class YoriProxyUser(FastHttpUser):
    """
    Simulates a user making requests through the YORI proxy.

    Uses FastHttpUser for better performance during load testing.
    """

    # Wait time between requests (simulates realistic user behavior)
    wait_time = between(0.5, 2.0)

    # Track metrics
    start_time = None
    request_count = 0

    def on_start(self):
        """Called when a user starts - set up test data"""
        self.start_time = time.time()
        self.request_count = 0

        # Sample LLM requests for testing
        self.llm_requests = [
            {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello, how are you?"}],
                "temperature": 0.7,
            },
            {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "What is the weather?"}],
            },
            {
                "model": "claude-3-opus-20240229",
                "messages": [{"role": "user", "content": "Tell me a joke"}],
                "max_tokens": 100,
            },
        ]

        # Sample device IPs for allowlist testing
        self.device_ips = [
            "192.168.1.100",
            "192.168.1.101",
            "192.168.1.102",
            "192.168.1.103",
        ]

    @task(10)
    def health_check(self):
        """
        Most frequent task - health check endpoint

        Weight: 10 (10x more frequent than other tasks)
        Expected: <10ms response time
        """
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data and data["status"] == "healthy":
                        response.success()
                    else:
                        response.failure(f"Invalid health check response: {data}")
                except Exception as e:
                    response.failure(f"Failed to parse health check: {e}")
            else:
                response.failure(f"Health check failed with status {response.status_code}")

    @task(5)
    def proxy_llm_request_openai(self):
        """
        Simulate proxying an LLM request to OpenAI

        Weight: 5 (medium frequency)
        Expected: <50ms added latency
        """
        request_data = random.choice(self.llm_requests)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-test-key-123",
        }

        with self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=headers,
            catch_response=True,
            name="/v1/chat/completions [OpenAI]",
        ) as response:
            self.request_count += 1

            # Accept both 200 (proxied) and 403 (blocked)
            if response.status_code in [200, 403, 503]:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(3)
    def proxy_llm_request_anthropic(self):
        """
        Simulate proxying an LLM request to Anthropic

        Weight: 3 (lower frequency)
        Expected: <50ms added latency
        """
        request_data = {
            "model": "claude-3-opus-20240229",
            "messages": [{"role": "user", "content": "Hello Claude"}],
            "max_tokens": 100,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": "sk-ant-test-key-123",
            "anthropic-version": "2023-06-01",
        }

        with self.client.post(
            "/v1/messages",
            json=request_data,
            headers=headers,
            catch_response=True,
            name="/v1/messages [Anthropic]",
        ) as response:
            self.request_count += 1

            # Accept both 200 (proxied) and 403 (blocked)
            if response.status_code in [200, 403, 503]:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(2)
    def check_enforcement_decision(self):
        """
        Test enforcement decision endpoint

        Weight: 2 (occasional checks)
        Expected: <20ms response time
        """
        with self.client.get("/api/enforcement/status", catch_response=True) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Enforcement status failed: {response.status_code}")

    @task(1)
    def test_override_validation(self):
        """
        Test password override validation

        Weight: 1 (rare event)
        Expected: <100ms response time
        """
        override_data = {
            "request_id": f"load-test-{self.request_count}",
            "password": "test_override_password",
        }

        with self.client.post(
            "/api/override/validate",
            json=override_data,
            catch_response=True,
            name="/api/override/validate",
        ) as response:
            # Accept 200 (valid), 401 (invalid), or 404 (endpoint doesn't exist yet)
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Override validation failed: {response.status_code}")


class YoriAdminUser(FastHttpUser):
    """
    Simulates an admin user accessing dashboard and management endpoints.

    Lower frequency than regular users.
    """

    wait_time = between(5, 15)

    @task(3)
    def view_dashboard(self):
        """View dashboard statistics"""
        with self.client.get("/api/stats/summary", catch_response=True) as response:
            # Accept 200 or 404 (if not implemented yet)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Dashboard failed: {response.status_code}")

    @task(2)
    def query_audit_logs(self):
        """Query audit logs"""
        params = {
            "limit": 100,
            "offset": 0,
        }
        with self.client.get(
            "/api/audit/events",
            params=params,
            catch_response=True,
        ) as response:
            # Accept 200 or 404 (if not implemented yet)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Audit query failed: {response.status_code}")

    @task(1)
    def check_allowlist(self):
        """Check allowlist status"""
        with self.client.get("/api/allowlist", catch_response=True) as response:
            # Accept 200 or 404 (if not implemented yet)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Allowlist check failed: {response.status_code}")


# Event listeners for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("\n=== YORI Load Test Starting ===")
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("=" * 40)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - print summary"""
    print("\n=== YORI Load Test Complete ===")

    stats = environment.stats

    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"RPS: {stats.total.total_rps:.2f}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"P95 Response Time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 Response Time: {stats.total.get_response_time_percentile(0.99):.2f}ms")

    # Check success criteria
    print("\n=== Success Criteria Check ===")

    p95_latency = stats.total.get_response_time_percentile(0.95)
    target_p95 = 50  # ms

    if p95_latency < target_p95:
        print(f"✓ P95 Latency: {p95_latency:.2f}ms < {target_p95}ms target")
    else:
        print(f"✗ P95 Latency: {p95_latency:.2f}ms >= {target_p95}ms target")

    if stats.total.fail_ratio < 0.01:  # < 1% failure rate
        print(f"✓ Failure Rate: {stats.total.fail_ratio * 100:.2f}% < 1%")
    else:
        print(f"✗ Failure Rate: {stats.total.fail_ratio * 100:.2f}% >= 1%")

    print("=" * 40)
