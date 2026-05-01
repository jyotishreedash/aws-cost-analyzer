#!/usr/bin/env python3
"""
AWS Infrastructure Cost Analyzer
Analyzes EC2, S3, RDS and generates a cost optimization report.
"""

import argparse
import sys
import os
import boto3
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from aws_cost_analyzer.ec2_analyzer import get_ec2_instances
from aws_cost_analyzer.s3_analyzer import get_s3_buckets
from aws_cost_analyzer.rds_analyzer import get_rds_instances
from aws_cost_analyzer.cost_explorer import get_cost_summary
from aws_cost_analyzer.report_generator import generate_html_report

console = Console() if RICH_AVAILABLE else None


def print_banner():
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]⚡ AWS Infrastructure Cost Analyzer[/bold cyan]\n"
            "[dim]Identify idle resources · Optimize spend · Generate reports[/dim]",
            border_style="cyan"
        ))
    else:
        print("=" * 50)
        print("  AWS Infrastructure Cost Analyzer")
        print("=" * 50)


def run_analysis(profile: str, region: str, output: str, skip_costs: bool):
    print_banner()

    # Create boto3 session
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
        if RICH_AVAILABLE:
            console.print(f"[green]✓[/green] Connected to AWS account: [bold]{account_id}[/bold] | Region: [bold]{region}[/bold]\n")
        else:
            print(f"Connected: Account {account_id} | Region {region}")
    except Exception as e:
        print(f"[ERROR] Could not connect to AWS: {e}")
        print("Make sure your AWS credentials are configured (aws configure or env vars)")
        sys.exit(1)

    data = {}

    # Analyze EC2
    _log("Analyzing EC2 instances...")
    try:
        data["ec2"] = get_ec2_instances(session)
        _log(f"Found {len(data['ec2'])} EC2 instances", success=True)
    except Exception as e:
        _log(f"EC2 analysis failed: {e}", error=True)
        data["ec2"] = []

    # Analyze S3
    _log("Analyzing S3 buckets...")
    try:
        data["s3"] = get_s3_buckets(session)
        _log(f"Found {len(data['s3'])} S3 buckets", success=True)
    except Exception as e:
        _log(f"S3 analysis failed: {e}", error=True)
        data["s3"] = []

    # Analyze RDS
    _log("Analyzing RDS instances...")
    try:
        data["rds"] = get_rds_instances(session)
        _log(f"Found {len(data['rds'])} RDS instances", success=True)
    except Exception as e:
        _log(f"RDS analysis failed: {e}", error=True)
        data["rds"] = []

    # Cost Explorer
    if not skip_costs:
        _log("Fetching cost data from Cost Explorer...")
        try:
            data["costs"] = get_cost_summary(session)
            _log(f"Total spend (30d): ${data['costs']['total_cost_usd']}", success=True)
        except Exception as e:
            _log(f"Cost Explorer failed (may need billing permissions): {e}", error=True)
            data["costs"] = {}
    else:
        data["costs"] = {}

    # Print quick summary to terminal
    _print_summary(data)

    # Generate HTML report
    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
    report_path = generate_html_report(data, output)

    if RICH_AVAILABLE:
        console.print(f"\n[bold green]✓ Report saved:[/bold green] {report_path}")
    else:
        print(f"\nReport saved: {report_path}")


def _log(msg, success=False, error=False):
    if RICH_AVAILABLE:
        if success:
            console.print(f"  [green]✓[/green] {msg}")
        elif error:
            console.print(f"  [red]✗[/red] {msg}")
        else:
            console.print(f"  [cyan]→[/cyan] {msg}")
    else:
        print(f"  {'OK' if success else 'ERR' if error else '..'} {msg}")


def _print_summary(data):
    if not RICH_AVAILABLE:
        return

    ec2 = data.get("ec2", [])
    s3 = data.get("s3", [])
    rds = data.get("rds", [])

    idle = [i for i in ec2 if i["status"] == "idle"]
    underutilized = [i for i in ec2 if i["status"] == "underutilized"]
    s3_issues = [b for b in s3 if b["status"] == "needs_attention"]
    rds_issues = [r for r in rds if r["health"] == "needs_attention"]

    console.print("\n")
    table = Table(title="🔍 Analysis Summary", border_style="dim")
    table.add_column("Resource", style="bold")
    table.add_column("Total", justify="center")
    table.add_column("Issues Found", justify="center")

    table.add_row("EC2 Instances", str(len(ec2)), f"[red]{len(idle)} idle[/red], [yellow]{len(underutilized)} underutilized[/yellow]")
    table.add_row("S3 Buckets", str(len(s3)), f"[yellow]{len(s3_issues)} need attention[/yellow]")
    table.add_row("RDS Instances", str(len(rds)), f"[yellow]{len(rds_issues)} need attention[/yellow]")

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="AWS Infrastructure Cost Analyzer — Find idle resources and optimize spend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --profile prod --region us-west-2
  python main.py --output reports/my-report.html
  python main.py --skip-costs
        """
    )
    parser.add_argument("--profile", default="default", help="AWS profile name (default: default)")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--output", default="reports/cost_report.html", help="Output HTML report path")
    parser.add_argument("--skip-costs", action="store_true", help="Skip Cost Explorer (needs billing permissions)")

    args = parser.parse_args()
    run_analysis(args.profile, args.region, args.output, args.skip_costs)


if __name__ == "__main__":
    main()
