#!/usr/bin/env python3
"""
Analyze YORI Proxy for Performance Bottlenecks

This script performs static analysis of the proxy implementation to identify:
- Missing connection pooling
- Blocking operations in async code
- Memory inefficiencies
- Missing caching opportunities
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Bottleneck:
    """Represents a performance bottleneck"""
    category: str
    severity: str  # 'critical', 'major', 'minor'
    location: str
    description: str
    recommendation: str
    line_number: int = 0


class ProxyAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze proxy code for performance issues"""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.split('\n')
        self.bottlenecks: List[Bottleneck] = []
        self.has_connection_pooling = False
        self.has_caching = False
        self.current_class = None
        self.current_function = None

    def visit_ClassDef(self, node):
        """Track current class"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_AsyncFunctionDef(self, node):
        """Analyze async functions for blocking operations"""
        old_function = self.current_function
        self.current_function = node.name

        # Check for blocking calls in async functions
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Check for httpx.Client (sync) instead of httpx.AsyncClient
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id == 'httpx' and child.func.attr == 'Client':
                            self.bottlenecks.append(Bottleneck(
                                category='Blocking I/O',
                                severity='critical',
                                location=f'{self.current_class}.{self.current_function}' if self.current_class else self.current_function,
                                description='Using synchronous httpx.Client in async function',
                                recommendation='Use httpx.AsyncClient for async operations',
                                line_number=child.lineno
                            ))

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node):
        """Check for httpx.AsyncClient creation patterns"""
        # Check for AsyncClient instantiation
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'httpx' and node.func.attr == 'AsyncClient':
                    # Check if it has connection limits
                    has_limits = False
                    for keyword in node.keywords:
                        if keyword.arg == 'limits':
                            has_limits = True
                            self.has_connection_pooling = True

                    if not has_limits:
                        location = f'{self.current_class}.{self.current_function}' if self.current_class and self.current_function else 'global'
                        self.bottlenecks.append(Bottleneck(
                            category='Connection Pooling',
                            severity='critical',
                            location=location,
                            description='httpx.AsyncClient created without connection limits',
                            recommendation='Add limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)',
                            line_number=node.lineno
                        ))

        self.generic_visit(node)


def analyze_proxy_file(file_path: Path) -> List[Bottleneck]:
    """Analyze proxy.py for performance bottlenecks"""
    bottlenecks = []

    with open(file_path, 'r') as f:
        source = f.read()

    # Parse AST
    try:
        tree = ast.parse(source)
        analyzer = ProxyAnalyzer(source)
        analyzer.visit(tree)
        bottlenecks.extend(analyzer.bottlenecks)

        # Check for missing connection pooling
        if not analyzer.has_connection_pooling:
            bottlenecks.append(Bottleneck(
                category='Connection Pooling',
                severity='critical',
                location='ProxyServer',
                description='No connection pooling configuration found',
                recommendation='Configure httpx.AsyncClient with Limits for connection reuse',
            ))

        # Check for caching implementation
        if 'cache' not in source.lower() and 'lru_cache' not in source.lower():
            bottlenecks.append(Bottleneck(
                category='Caching',
                severity='major',
                location='ProxyServer',
                description='No caching implementation found',
                recommendation='Implement in-memory cache for policy decisions and repeated requests',
            ))

        # Check for blocking operations
        if re.search(r'(?<!async\s)with\s+httpx\.Client', source):
            bottlenecks.append(Bottleneck(
                category='Blocking I/O',
                severity='critical',
                location='ProxyServer',
                description='Synchronous httpx.Client usage detected',
                recommendation='Replace with httpx.AsyncClient and await calls',
            ))

        # Check for memory inefficiencies
        if re.search(r'await\s+request\.body\(\)', source):
            # This is actually correct, but we should note it loads full body into memory
            if 'stream' not in source.lower():
                bottlenecks.append(Bottleneck(
                    category='Memory Usage',
                    severity='minor',
                    location='proxy_request handler',
                    description='Request body loaded into memory (not streaming)',
                    recommendation='Consider streaming for large payloads (future optimization)',
                ))

    except SyntaxError as e:
        print(f"Error parsing {file_path}: {e}")

    return bottlenecks


def print_analysis_report(bottlenecks: List[Bottleneck]):
    """Print formatted analysis report"""

    print("\n" + "="*80)
    print("YORI PROXY PERFORMANCE ANALYSIS")
    print("="*80 + "\n")

    # Group by severity
    critical = [b for b in bottlenecks if b.severity == 'critical']
    major = [b for b in bottlenecks if b.severity == 'major']
    minor = [b for b in bottlenecks if b.severity == 'minor']

    print(f"Found {len(bottlenecks)} potential bottlenecks:")
    print(f"  🔴 Critical: {len(critical)}")
    print(f"  🟡 Major: {len(major)}")
    print(f"  🔵 Minor: {len(minor)}")
    print()

    # Print critical issues first
    if critical:
        print("=" * 80)
        print("🔴 CRITICAL ISSUES")
        print("=" * 80)
        for i, b in enumerate(critical, 1):
            print(f"\n{i}. [{b.category}] {b.location}")
            if b.line_number:
                print(f"   Line: {b.line_number}")
            print(f"   Issue: {b.description}")
            print(f"   Fix: {b.recommendation}")

    # Print major issues
    if major:
        print("\n" + "=" * 80)
        print("🟡 MAJOR ISSUES")
        print("=" * 80)
        for i, b in enumerate(major, 1):
            print(f"\n{i}. [{b.category}] {b.location}")
            print(f"   Issue: {b.description}")
            print(f"   Fix: {b.recommendation}")

    # Print minor issues
    if minor:
        print("\n" + "=" * 80)
        print("🔵 MINOR ISSUES")
        print("=" * 80)
        for i, b in enumerate(minor, 1):
            print(f"\n{i}. [{b.category}] {b.location}")
            print(f"   Issue: {b.description}")
            print(f"   Fix: {b.recommendation}")

    print("\n" + "=" * 80)
    print("RECOMMENDED ACTIONS")
    print("=" * 80)
    print("""
1. Implement Connection Pooling (CRITICAL)
   - Configure httpx.AsyncClient with connection limits
   - Reuse client instance across requests
   - Target: Reduce connection overhead by 80%

2. Add Request/Response Caching (MAJOR)
   - Implement in-memory cache with TTL
   - Cache policy evaluation results
   - Cache repeated upstream requests
   - Target: 30%+ cache hit rate

3. Optimize Memory Usage (MINOR)
   - Profile memory usage under load
   - Consider streaming for large payloads
   - Target: <100MB under load

4. Improve Async Patterns (if applicable)
   - Remove any blocking I/O operations
   - Use asyncio.gather for concurrent operations
   - Target: Maximum concurrent throughput
    """)

    print("=" * 80 + "\n")


def main():
    """Run bottleneck analysis"""

    # Find proxy.py
    proxy_file = Path("python/yori/proxy.py")

    if not proxy_file.exists():
        print(f"Error: {proxy_file} not found")
        print("Run this script from the repository root")
        return

    print("Analyzing proxy implementation...")
    bottlenecks = analyze_proxy_file(proxy_file)

    print_analysis_report(bottlenecks)

    # Save report to file
    report_file = "performance_analysis.txt"
    with open(report_file, 'w') as f:
        # Redirect stdout to file temporarily
        import sys
        old_stdout = sys.stdout
        sys.stdout = f
        print_analysis_report(bottlenecks)
        sys.stdout = old_stdout

    print(f"Analysis report saved to {report_file}")


if __name__ == "__main__":
    main()
