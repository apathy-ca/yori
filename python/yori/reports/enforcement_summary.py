"""
YORI Enforcement Summary Report Generator

Generates weekly/monthly enforcement reports with statistics,
trends, and policy effectiveness analysis.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import json

from yori.enforcement_stats import EnforcementStatsCalculator


class EnforcementReportGenerator:
    """Generates enforcement summary reports"""

    def __init__(self, database_path: Path):
        """
        Initialize report generator.

        Args:
            database_path: Path to SQLite audit database
        """
        self.database_path = database_path
        self.stats = EnforcementStatsCalculator(database_path)

    def generate_text_report(self, days: int = 7) -> str:
        """
        Generate text-based enforcement report.

        Args:
            days: Number of days to analyze

        Returns:
            Formatted text report
        """
        # Get data
        summary = self.stats.get_enforcement_summary(days=days)
        daily_stats = self.stats.get_daily_stats(days=days)
        top_policies = self.stats.get_top_blocking_policies(limit=10, days=days)
        recent_blocks = self.stats.get_recent_blocks(limit=10)

        # Build report
        report = []
        report.append("=" * 80)
        report.append("YORI ENFORCEMENT SUMMARY REPORT")
        report.append("=" * 80)
        report.append("")

        # Report period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        report.append(f"Report Period: {start_date.date()} to {end_date.date()}")
        report.append(f"Generated: {end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")

        # Executive Summary
        report.append("-" * 80)
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 80)
        report.append("")
        report.append(f"Total Blocks:              {summary.total_blocks:,}")
        report.append(f"Total Overrides:           {summary.total_overrides:,}")
        report.append(f"Total Allowlist Bypasses:  {summary.total_bypasses:,}")
        report.append(f"Total Advisory Alerts:     {summary.total_alerts:,}")
        report.append(f"Total Allowed Requests:    {summary.total_allows:,}")
        report.append("")
        report.append(f"Override Success Rate:     {summary.override_success_rate:.1f}%")
        report.append("")

        if summary.top_blocking_policy:
            report.append(f"Top Blocking Policy:       {summary.top_blocking_policy}")
        if summary.most_blocked_client:
            report.append(f"Most Blocked Client:       {summary.most_blocked_client}")
        report.append("")

        # Daily Trends
        if daily_stats:
            report.append("-" * 80)
            report.append("DAILY TRENDS")
            report.append("-" * 80)
            report.append("")
            report.append(
                f"{'Date':<12} {'Blocks':>8} {'Overrides':>10} {'Bypasses':>10} {'Alerts':>8}"
            )
            report.append("-" * 50)

            for stat in reversed(daily_stats[:14]):  # Last 14 days
                report.append(
                    f"{stat.date:<12} {stat.blocks:>8} {stat.overrides:>10} "
                    f"{stat.bypasses:>10} {stat.alerts:>8}"
                )
            report.append("")

        # Top Blocking Policies
        if top_policies:
            report.append("-" * 80)
            report.append("TOP BLOCKING POLICIES")
            report.append("-" * 80)
            report.append("")
            report.append(f"{'#':<4} {'Policy Name':<40} {'Blocks':>10} {'Clients':>10}")
            report.append("-" * 66)

            for i, policy in enumerate(top_policies, 1):
                report.append(
                    f"{i:<4} {policy.policy_name:<40} {policy.block_count:>10} "
                    f"{policy.affected_clients:>10}"
                )
            report.append("")

        # Recent Block Events
        if recent_blocks:
            report.append("-" * 80)
            report.append("RECENT BLOCK EVENTS (Last 10)")
            report.append("-" * 80)
            report.append("")

            for block in recent_blocks:
                timestamp = datetime.fromisoformat(block.timestamp.replace('Z', '+00:00'))
                report.append(f"Time:     {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                report.append(f"Client:   {block.client_device or block.client_ip}")
                report.append(f"Endpoint: {block.endpoint}")
                report.append(f"Policy:   {block.policy_name}")
                report.append(f"Reason:   {block.reason}")
                report.append(f"Action:   {block.enforcement_action}")
                if block.override_user:
                    report.append(f"Override: {block.override_user}")
                report.append("")

        # Footer
        report.append("-" * 80)
        report.append("END OF REPORT")
        report.append("-" * 80)

        return "\n".join(report)

    def generate_json_report(self, days: int = 7) -> dict:
        """
        Generate JSON enforcement report.

        Args:
            days: Number of days to analyze

        Returns:
            Report data as dictionary
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        summary = self.stats.get_enforcement_summary(days=days)
        daily_stats = self.stats.get_daily_stats(days=days)
        top_policies = self.stats.get_top_blocking_policies(limit=10, days=days)
        recent_blocks = self.stats.get_recent_blocks(limit=10)

        return {
            "report_type": "enforcement_summary",
            "period": {
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "days": days,
            },
            "generated_at": end_date.isoformat() + "Z",
            "summary": {
                "total_blocks": summary.total_blocks,
                "total_overrides": summary.total_overrides,
                "total_bypasses": summary.total_bypasses,
                "total_alerts": summary.total_alerts,
                "total_allows": summary.total_allows,
                "override_success_rate": summary.override_success_rate,
                "top_blocking_policy": summary.top_blocking_policy,
                "most_blocked_client": summary.most_blocked_client,
            },
            "daily_stats": [
                {
                    "date": stat.date,
                    "blocks": stat.blocks,
                    "overrides": stat.overrides,
                    "bypasses": stat.bypasses,
                    "alerts": stat.alerts,
                    "allows": stat.allows,
                }
                for stat in daily_stats
            ],
            "top_policies": [
                {
                    "policy_name": policy.policy_name,
                    "block_count": policy.block_count,
                    "affected_clients": policy.affected_clients,
                }
                for policy in top_policies
            ],
            "recent_blocks": [
                {
                    "timestamp": block.timestamp,
                    "client_ip": block.client_ip,
                    "client_device": block.client_device,
                    "endpoint": block.endpoint,
                    "policy_name": block.policy_name,
                    "reason": block.reason,
                    "enforcement_action": block.enforcement_action,
                    "override_user": block.override_user,
                }
                for block in recent_blocks
            ],
        }

    def save_report(
        self, output_path: Path, format: str = "text", days: int = 7
    ) -> None:
        """
        Generate and save report to file.

        Args:
            output_path: Path to save report
            format: Report format ('text' or 'json')
            days: Number of days to analyze
        """
        if format == "json":
            report_data = self.generate_json_report(days=days)
            with open(output_path, "w") as f:
                json.dump(report_data, f, indent=2)
        else:  # text
            report_text = self.generate_text_report(days=days)
            with open(output_path, "w") as f:
                f.write(report_text)

        print(f"Report saved to: {output_path}")


def main():
    """CLI entry point for report generation"""
    parser = argparse.ArgumentParser(
        description="Generate YORI enforcement summary report"
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("/var/db/yori/audit.db"),
        help="Path to audit database (default: /var/db/yori/audit.db)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: stdout for text, enforcement_report.json for json)",
    )

    args = parser.parse_args()

    # Generate report
    generator = EnforcementReportGenerator(args.database)

    if args.output:
        generator.save_report(args.output, format=args.format, days=args.days)
    else:
        if args.format == "json":
            report = generator.generate_json_report(days=args.days)
            print(json.dumps(report, indent=2))
        else:
            report = generator.generate_text_report(days=args.days)
            print(report)


if __name__ == "__main__":
    main()
