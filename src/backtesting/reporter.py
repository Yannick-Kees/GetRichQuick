# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Generate backtest reports."""
import json
from datetime import datetime
from pathlib import Path

from .engine import BacktestResult
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def save_backtest_results(result: BacktestResult, output_path: Path) -> None:
    """
    Save backtest results to JSON file.

    Args:
        result: BacktestResult object
        output_path: Path to save JSON file
    """
    try:
        # Convert to dictionary
        output_dict = {
            "metadata": {
                "backtest_date": datetime.now().isoformat(),
                "total_trades": result.total_trades,
                "closed_trades": result.total_trades - result.still_open,
                "still_open": result.still_open,
                "winning_trades": result.winning_trades,
                "losing_trades": result.losing_trades,
                "total_pnl": round(result.total_pnl, 2),
                "total_invested": round(result.total_invested, 2),
                "return_pct": (
                    round(result.total_pnl / result.total_invested * 100, 2)
                    if result.total_invested > 0
                    else 0
                ),
                "avg_holding_days": round(result.avg_holding_days, 1),
            },
            "holding_days_distribution": result.holding_days_distribution,
            "trades": [
                {
                    "ticker": t.ticker,
                    "company_name": t.company_name,
                    "entry_date": t.entry_date,
                    "entry_price": round(t.entry_price, 2),
                    "shares": round(t.shares, 4),
                    "target_price": round(t.target_price, 2),
                    "exit_date": t.exit_date,
                    "exit_price": round(t.exit_price, 2) if t.exit_price else None,
                    "holding_days": t.holding_days,
                    "pnl": round(t.pnl, 2) if t.pnl is not None else None,
                    "pnl_pct": (
                        round(t.pnl / (t.entry_price * t.shares) * 100, 2)
                        if t.pnl is not None and t.entry_price * t.shares > 0
                        else None
                    ),
                }
                for t in result.trades
            ],
        }

        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(output_dict, f, indent=2)

        logger.info(f"\nResults saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise


def print_backtest_summary(result: BacktestResult) -> None:
    """
    Print backtest summary to console.

    Args:
        result: BacktestResult object
    """
    print("\n" + "=" * 80)
    print("BACKTEST SUMMARY")
    print("=" * 80)

    # Overall metrics
    print("\nOverall Performance:")
    print(f"  Total trades: {result.total_trades}")
    print(f"  Closed trades: {result.total_trades - result.still_open}")
    print(f"  Still open: {result.still_open}")
    print(f"  Winning trades: {result.winning_trades}")
    print(f"  Losing trades: {result.losing_trades}")

    if result.total_trades - result.still_open > 0:
        win_rate = result.winning_trades / (result.total_trades - result.still_open) * 100
        print(f"  Win rate: {win_rate:.1f}%")

    print(f"\n  Total P&L: ${result.total_pnl:.2f}")
    print(f"  Total invested: ${result.total_invested:.2f}")

    if result.total_invested > 0:
        return_pct = result.total_pnl / result.total_invested * 100
        print(f"  Return: {return_pct:.2f}%")

    print(f"\n  Average holding period: {result.avg_holding_days:.1f} days")

    # Holding period distribution
    if result.holding_days_distribution:
        print("\nHolding Period Distribution:")
        # Sort by order
        order = [
            "0-7 days",
            "7-14 days",
            "14-30 days",
            "30-60 days",
            "60-90 days",
            "90-180 days",
            "180-365 days",
            "365+ days",
        ]
        for period in order:
            if period in result.holding_days_distribution:
                count = result.holding_days_distribution[period]
                pct = count / (result.total_trades - result.still_open) * 100
                bar = "█" * int(pct / 2)  # Scale to 50 chars max
                print(f"  {period:15s} : {count:3d} ({pct:5.1f}%) {bar}")

    # Top/bottom trades
    closed_trades = [t for t in result.trades if t.pnl is not None]
    if closed_trades:
        closed_trades.sort(key=lambda t: t.pnl, reverse=True)

        print("\nTop 5 Winners:")
        for i, trade in enumerate(closed_trades[:5], 1):
            pnl_pct = trade.pnl / (trade.entry_price * trade.shares) * 100
            print(
                f"  {i}. {trade.ticker:6s} - ${trade.pnl:7.2f} ({pnl_pct:+6.1f}%) "
                f"- {trade.holding_days:3d} days - {trade.entry_date} to {trade.exit_date}"
            )

        if len(closed_trades) >= 5:
            print("\nTop 5 Losers:")
            for i, trade in enumerate(closed_trades[-5:][::-1], 1):
                pnl_pct = trade.pnl / (trade.entry_price * trade.shares) * 100
                print(
                    f"  {i}. {trade.ticker:6s} - ${trade.pnl:7.2f} ({pnl_pct:+6.1f}%) "
                    f"- {trade.holding_days:3d} days - {trade.entry_date} to {trade.exit_date}"
                )

    print("=" * 80)
