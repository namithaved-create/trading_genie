"""Command-line portfolio health check: python -m trading_genie data/sample_portfolio.csv"""

from __future__ import annotations

import argparse
import sys

import anthropic

from .coach import DISCLAIMER, MissingCredentials, explain
from .portfolio import analyze, load_holdings


def main() -> int:
    parser = argparse.ArgumentParser(description="Trading Genie portfolio health check")
    parser.add_argument("csv", help="Path to a portfolio CSV (see data/sample_portfolio.csv)")
    parser.add_argument("--no-ai", action="store_true", help="Show the numbers only, skip Claude")
    args = parser.parse_args()

    try:
        report = analyze(load_holdings(args.csv))
    except (OSError, ValueError) as e:
        print(f"Couldn't read portfolio: {e}", file=sys.stderr)
        return 1

    print(f"Portfolio value:   ${report.total_value:,.2f}")
    print(f"Health score:      {report.score}/100")
    print(f"Avg. fund fees:    {report.weighted_expense_ratio:.2%} (~${report.annual_fees:,.0f}/year)")
    print(f"Behaves like:      {report.effective_holdings:.1f} holdings\n")
    print("Holdings:")
    for h in report.holdings:
        print(f"  {h['symbol']:<6} {h['weight_pct']:>5.1f}%  ${h['value']:>10,.2f}  {h['sector']}")
    print("\nSectors:")
    for sector, pct in report.sector_weights.items():
        print(f"  {sector:<24} {pct:>5.1f}%")
    print("\nFlags:")
    for flag in report.flags or []:
        print(f"  [{flag.severity.upper()}] {flag.title}\n      {flag.detail}")
    if not report.flags:
        print("  None. Nicely balanced!")

    if not args.no_ai:
        print("\n--- Trading Genie explains ---\n")
        try:
            print(explain(report))
        except MissingCredentials:
            print("Claude needs an API key: set ANTHROPIC_API_KEY, or run with --no-ai.", file=sys.stderr)
            return 1
        except anthropic.AuthenticationError:
            print("Claude rejected the API key. Check ANTHROPIC_API_KEY.", file=sys.stderr)
            return 1
        except anthropic.APIConnectionError:
            print("Couldn't reach Claude. Check your internet connection.", file=sys.stderr)
            return 1
        except anthropic.APIStatusError as e:
            print(f"Claude API error ({e.status_code}): {e.message}", file=sys.stderr)
            return 1

    print(f"\n{DISCLAIMER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
