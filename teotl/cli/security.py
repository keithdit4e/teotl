"""Security management CLI commands.

Provides commands for viewing audit logs, generating compliance reports,
and managing security policies.

Usage:
    forge security logs [options]
    forge security report [options]
    forge security status <agent-id>
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from teotl.core.security.audit import AuditLogger
from teotl.core.security.policy import SecurityPolicy


class Color:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Color.BOLD}{Color.CYAN}{text}{Color.END}")
    print("=" * len(text))


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Color.GREEN}✅ {text}{Color.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Color.RED}❌ {text}{Color.END}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Color.BLUE}ℹ️  {text}{Color.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Color.YELLOW}⚠️  {text}{Color.END}")


def view_logs(args: argparse.Namespace) -> None:
    """View audit logs with filtering."""
    workspace_dir = Path(args.workspace).expanduser().resolve()

    if not workspace_dir.exists():
        print_error(f"Workspace not found: {workspace_dir}")
        sys.exit(1)

    # Load security policy to get agent ID
    policy_path = workspace_dir / "security.yaml"
    if not policy_path.exists():
        print_error(f"Security policy not found: {policy_path}")
        print_info("This agent doesn't have security enabled.")
        sys.exit(1)

    try:
        policy = SecurityPolicy.from_file(policy_path)
    except Exception as e:
        print_error(f"Failed to load security policy: {e}")
        sys.exit(1)

    # Create audit logger
    audit = AuditLogger(policy, workspace_dir)

    # Parse date filters
    start_date = None
    end_date = None

    if args.days:
        start_date = datetime.now() - timedelta(days=args.days)
    elif args.start:
        try:
            start_date = datetime.fromisoformat(args.start)
        except ValueError:
            print_error(f"Invalid start date format: {args.start}")
            print_info("Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
            sys.exit(1)

    if args.end:
        try:
            end_date = datetime.fromisoformat(args.end)
        except ValueError:
            print_error(f"Invalid end date format: {args.end}")
            print_info("Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
            sys.exit(1)

    # Parse event type filters
    event_types = None
    if args.type:
        event_types = args.type.split(",")

    # Read logs
    try:
        entries = audit.read_logs(
            start_date=start_date,
            end_date=end_date,
            event_types=event_types,
            violations_only=args.violations_only,
        )
    except Exception as e:
        print_error(f"Failed to read logs: {e}")
        sys.exit(1)

    if not entries:
        print_info("No log entries found matching filters.")
        return

    # Print header
    print_header(f"Audit Logs: {policy.agent_id}")

    # Print filters
    filter_info = []
    if start_date:
        filter_info.append(f"From: {start_date.strftime('%Y-%m-%d %H:%M')}")
    if end_date:
        filter_info.append(f"To: {end_date.strftime('%Y-%m-%d %H:%M')}")
    if event_types:
        filter_info.append(f"Types: {', '.join(event_types)}")
    if args.violations_only:
        filter_info.append("Violations only")

    if filter_info:
        print(f"\n{Color.CYAN}Filters:{Color.END} {' | '.join(filter_info)}")

    print(f"\n{Color.BOLD}Found {len(entries)} entries{Color.END}\n")

    # Print entries
    for i, entry in enumerate(entries[-args.limit :], 1):
        _print_log_entry(entry, verbose=args.verbose)

        # Add separator between entries
        if i < len(entries) and args.verbose:
            print("-" * 80)


def _print_log_entry(entry: Any, verbose: bool = False) -> None:
    """Print a single log entry."""
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(entry.timestamp)
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        time_str = entry.timestamp

    # Color-code by event type
    if not entry.allowed:
        color = Color.RED
        marker = "❌"
    elif entry.event_type == "tool_call":
        color = Color.GREEN
        marker = "✅"
    elif entry.event_type == "policy_violation":
        color = Color.RED
        marker = "🚫"
    elif entry.event_type == "cost_limit":
        color = Color.YELLOW
        marker = "💰"
    elif entry.event_type == "rate_limit":
        color = Color.YELLOW
        marker = "⏱️"
    else:
        color = Color.CYAN
        marker = "ℹ️"

    # Basic info
    print(f"{color}{marker} [{time_str}] {entry.event_type}{Color.END}", end="")

    if entry.tool:
        print(f" - {Color.BOLD}{entry.tool}{Color.END}", end="")

    if not entry.allowed:
        print(f" {Color.RED}(BLOCKED){Color.END}", end="")

    print()  # Newline

    # Verbose details
    if verbose:
        if entry.violation_reason:
            print(f"  Reason: {entry.violation_reason}")

        if entry.args and not entry.pii_redacted:
            args_str = json.dumps(entry.args, indent=2)
            # Indent each line
            args_str = "\n  ".join(args_str.split("\n"))
            print(f"  Args: {args_str}")
        elif entry.pii_redacted:
            print("  Args: [PII REDACTED]")

        if entry.result_summary:
            print(f"  Result: {entry.result_summary}")

        if entry.duration_ms:
            print(f"  Duration: {entry.duration_ms}ms")

        if entry.cost:
            print(f"  Cost: ${entry.cost:.4f}")

        if entry.tokens_used:
            print(f"  Tokens: {entry.tokens_used}")

        # Compliance fields
        if entry.gdpr_data_subject:
            print(f"  GDPR Subject: {entry.gdpr_data_subject}")
        if entry.gdpr_purpose:
            print(f"  GDPR Purpose: {entry.gdpr_purpose}")

        if entry.soc2_auth_method:
            print(f"  SOC2 Auth: {entry.soc2_auth_method}")

        if entry.hipaa_phi_accessed:
            print("  HIPAA PHI: Accessed")
            if entry.hipaa_access_justification:
                print(f"  HIPAA Justification: {entry.hipaa_access_justification}")


def generate_report(args: argparse.Namespace) -> None:
    """Generate compliance report."""
    workspace_dir = Path(args.workspace).expanduser().resolve()

    if not workspace_dir.exists():
        print_error(f"Workspace not found: {workspace_dir}")
        sys.exit(1)

    # Load security policy
    policy_path = workspace_dir / "security.yaml"
    if not policy_path.exists():
        print_error(f"Security policy not found: {policy_path}")
        sys.exit(1)

    try:
        policy = SecurityPolicy.from_file(policy_path)
    except Exception as e:
        print_error(f"Failed to load security policy: {e}")
        sys.exit(1)

    # Create audit logger
    audit = AuditLogger(policy, workspace_dir)

    # Determine report period
    if args.days:
        start_date = datetime.now() - timedelta(days=args.days)
    else:
        start_date = datetime.now() - timedelta(days=30)  # Default to 30 days

    end_date = datetime.now()

    # Read all logs in period
    try:
        entries = audit.read_logs(start_date=start_date, end_date=end_date)
    except Exception as e:
        print_error(f"Failed to read logs: {e}")
        sys.exit(1)

    # Generate report
    print_header(f"Compliance Report: {policy.agent_id}")

    print(f"\n{Color.BOLD}Report Period:{Color.END}")
    print(f"  From: {start_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"  To:   {end_date.strftime('%Y-%m-%d %H:%M')}")

    print(f"\n{Color.BOLD}Policy Information:{Color.END}")
    print(f"  Version: {policy.version}")
    print(f"  Log Level: {policy.log_level.value}")
    print(f"  Network Mode: {policy.network.mode.value}")
    print(f"  Filesystem Mode: {policy.filesystem.mode.value}")

    print(f"\n{Color.BOLD}Compliance Features:{Color.END}")
    print(f"  GDPR: {'✅ Enabled' if policy.compliance.gdpr_enabled else '❌ Disabled'}")
    print(f"  SOC2: {'✅ Enabled' if policy.compliance.soc2_enabled else '❌ Disabled'}")
    print(f"  HIPAA: {'✅ Enabled' if policy.compliance.hipaa_enabled else '❌ Disabled'}")

    # Count events by type
    event_counts: dict[str, int] = {}
    violations = 0
    total_cost = 0.0

    for entry in entries:
        event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1
        if not entry.allowed:
            violations += 1
        if entry.cost:
            total_cost += entry.cost

    print(f"\n{Color.BOLD}Activity Summary:{Color.END}")
    print(f"  Total Events: {len(entries)}")
    print(f"  Violations: {Color.RED if violations > 0 else Color.GREEN}{violations}{Color.END}")
    print(f"  Total Cost: ${total_cost:.2f}")

    print(f"\n{Color.BOLD}Events by Type:{Color.END}")
    for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {event_type}: {count}")

    # Top tools
    tool_counts: dict[str, int] = {}
    for entry in entries:
        if entry.tool:
            tool_counts[entry.tool] = tool_counts.get(entry.tool, 0) + 1

    if tool_counts:
        print(f"\n{Color.BOLD}Top Tools Used:{Color.END}")
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {tool}: {count}")

    # Violations breakdown
    if violations > 0:
        print(f"\n{Color.BOLD}Violations Breakdown:{Color.END}")
        violation_types: dict[str, int] = {}
        for entry in entries:
            if not entry.allowed and entry.policy_violated:
                violation_types[entry.policy_violated] = (
                    violation_types.get(entry.policy_violated, 0) + 1
                )

        for vtype, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype}: {count}")

    # Save report if requested
    if args.output:
        output_path = Path(args.output)
        report_data = {
            "agent_id": policy.agent_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "policy": {
                "version": policy.version,
                "log_level": policy.log_level.value,
                "network_mode": policy.network.mode.value,
                "filesystem_mode": policy.filesystem.mode.value,
            },
            "compliance": {
                "gdpr_enabled": policy.compliance.gdpr_enabled,
                "soc2_enabled": policy.compliance.soc2_enabled,
                "hipaa_enabled": policy.compliance.hipaa_enabled,
            },
            "summary": {
                "total_events": len(entries),
                "violations": violations,
                "total_cost": total_cost,
            },
            "events_by_type": event_counts,
            "tools_used": tool_counts,
            "violations_by_type": violation_types if violations > 0 else {},
        }

        try:
            with open(output_path, "w") as f:
                json.dump(report_data, f, indent=2)
            print_success(f"\nReport saved to: {output_path}")
        except Exception as e:
            print_error(f"Failed to save report: {e}")


def show_status(args: argparse.Namespace) -> None:
    """Show current security status."""
    workspace_dir = Path(args.workspace).expanduser().resolve()

    if not workspace_dir.exists():
        print_error(f"Workspace not found: {workspace_dir}")
        sys.exit(1)

    # Load security policy
    policy_path = workspace_dir / "security.yaml"
    if not policy_path.exists():
        print_error(f"Security policy not found: {policy_path}")
        print_info("This agent doesn't have security enabled.")
        sys.exit(1)

    try:
        SecurityPolicy.from_file(policy_path)
    except Exception as e:
        print_error(f"Failed to load security policy: {e}")
        sys.exit(1)

    # Load enforcer to get current cost/rate status
    from teotl.core.security.enforcement import create_enforcer

    enforcer = create_enforcer(workspace_dir)
    if not enforcer:
        print_error("Failed to create security enforcer")
        sys.exit(1)

    status = enforcer.get_security_status()

    print_header(f"Security Status: {status['agent_id']}")

    print(f"\n{Color.BOLD}Policy:{Color.END}")
    print(f"  Version: {status['policy_version']}")
    print(f"  Log Level: {status['log_level']}")

    print(f"\n{Color.BOLD}Cost Limits:{Color.END}")
    costs = status["costs"]
    print(f"  Hourly:  ${costs['current']['hourly']:.2f} / ${costs['limits']['hourly']:.2f}")
    print(f"  Daily:   ${costs['current']['daily']:.2f} / ${costs['limits']['daily']:.2f}")
    print(f"  Monthly: ${costs['current']['monthly']:.2f} / ${costs['limits']['monthly']:.2f}")

    print(f"\n{Color.BOLD}Rate Limits:{Color.END}")
    rate = status["rate"]
    print(f"  Current: {rate['current_per_minute']} calls/min")
    print(f"  Limit:   {rate['limit_per_minute']} calls/min")

    print(f"\n{Color.BOLD}Compliance:{Color.END}")
    comp = status["compliance"]
    print(f"  GDPR:  {'✅ Enabled' if comp['gdpr'] else '❌ Disabled'}")
    print(f"  SOC2:  {'✅ Enabled' if comp['soc2'] else '❌ Disabled'}")
    print(f"  HIPAA: {'✅ Enabled' if comp['hipaa'] else '❌ Disabled'}")


def main() -> None:
    """Main entry point for security CLI."""
    parser = argparse.ArgumentParser(
        description="Forge Agent Security Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Security command")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View audit logs")
    logs_parser.add_argument(
        "--workspace",
        "-w",
        default="~/.forge/my-agent",
        help="Agent workspace directory (default: ~/.forge/my-agent)",
    )
    logs_parser.add_argument(
        "--days",
        "-d",
        type=int,
        help="Show logs from last N days",
    )
    logs_parser.add_argument(
        "--start",
        help="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
    )
    logs_parser.add_argument(
        "--end",
        help="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
    )
    logs_parser.add_argument(
        "--type",
        "-t",
        help="Filter by event types (comma-separated: tool_call,policy_violation,cost_limit)",
    )
    logs_parser.add_argument(
        "--violations-only",
        "-v",
        action="store_true",
        help="Show only violations",
    )
    logs_parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=50,
        help="Maximum number of entries to show (default: 50)",
    )
    logs_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed information",
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate compliance report")
    report_parser.add_argument(
        "--workspace",
        "-w",
        default="~/.forge/my-agent",
        help="Agent workspace directory (default: ~/.forge/my-agent)",
    )
    report_parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Report period in days (default: 30)",
    )
    report_parser.add_argument(
        "--output",
        "-o",
        help="Save report to JSON file",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show security status")
    status_parser.add_argument(
        "--workspace",
        "-w",
        default="~/.forge/my-agent",
        help="Agent workspace directory (default: ~/.forge/my-agent)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "logs":
        view_logs(args)
    elif args.command == "report":
        generate_report(args)
    elif args.command == "status":
        show_status(args)


if __name__ == "__main__":
    main()
