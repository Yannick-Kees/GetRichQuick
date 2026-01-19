# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Generate plots for backtest results."""
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .engine import BacktestResult
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def plot_cumulative_pnl(result: BacktestResult, output_path: Path) -> None:
    """
    Plot cumulative P&L over time.

    Args:
        result: BacktestResult object
        output_path: Path to save the plot
    """
    try:
        # Sort trades by exit date
        closed_trades = [t for t in result.trades if t.exit_date is not None]
        closed_trades.sort(key=lambda t: t.exit_date)

        if not closed_trades:
            logger.warning("No closed trades to plot")
            return

        # Calculate cumulative P&L
        dates = []
        cumulative_pnl = []
        current_pnl = 0.0

        for trade in closed_trades:
            exit_date = datetime.strptime(trade.exit_date, "%Y-%m-%d")
            current_pnl += trade.pnl
            dates.append(exit_date)
            cumulative_pnl.append(current_pnl)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot cumulative P&L
        ax.plot(dates, cumulative_pnl, linewidth=2, color="#2E86AB", marker="o", markersize=4)

        # Add horizontal line at y=0
        ax.axhline(y=0, color="gray", linestyle="--", linewidth=1, alpha=0.5)

        # Styling
        ax.set_xlabel("Date", fontsize=12, fontweight="bold")
        ax.set_ylabel("Cumulative P&L ($)", fontsize=12, fontweight="bold")
        ax.set_title(
            "Cumulative Profit & Loss Over Time", fontsize=14, fontweight="bold", pad=20
        )

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45, ha="right")

        # Grid
        ax.grid(True, alpha=0.3, linestyle="--")

        # Add final value annotation
        final_pnl = cumulative_pnl[-1]
        final_date = dates[-1]
        ax.annotate(
            f"Final: ${final_pnl:.2f}",
            xy=(final_date, final_pnl),
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="yellow", alpha=0.7),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )

        # Color the area under the curve
        ax.fill_between(
            dates,
            cumulative_pnl,
            0,
            where=[pnl >= 0 for pnl in cumulative_pnl],
            color="green",
            alpha=0.2,
            label="Profit",
        )
        ax.fill_between(
            dates,
            cumulative_pnl,
            0,
            where=[pnl < 0 for pnl in cumulative_pnl],
            color="red",
            alpha=0.2,
            label="Loss",
        )

        ax.legend(loc="upper left")

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Cumulative P&L plot saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to create cumulative P&L plot: {e}")


def plot_holding_period_distribution(result: BacktestResult, output_path: Path) -> None:
    """
    Plot distribution of holding periods.

    Args:
        result: BacktestResult object
        output_path: Path to save the plot
    """
    try:
        # Get holding days from closed trades
        holding_days = [t.holding_days for t in result.trades if t.holding_days is not None]

        if not holding_days:
            logger.warning("No holding period data to plot")
            return

        # Define bins
        bins = [0, 7, 14, 30, 60, 90, 180, 365, max(holding_days) + 1]
        labels = ["0-7", "7-14", "14-30", "30-60", "60-90", "90-180", "180-365", "365+"]

        # Count trades in each bin
        counts = []
        for i in range(len(bins) - 1):
            count = sum(1 for days in holding_days if bins[i] <= days < bins[i + 1])
            counts.append(count)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Create bar chart
        colors = plt.cm.viridis([i / len(counts) for i in range(len(counts))])
        bars = ax.bar(labels, counts, color=colors, edgecolor="black", linewidth=1.2)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=11,
                    fontweight="bold",
                )

        # Styling
        ax.set_xlabel("Holding Period (Days)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Number of Trades", fontsize=12, fontweight="bold")
        ax.set_title(
            "Distribution of Holding Periods", fontsize=14, fontweight="bold", pad=20
        )

        # Grid
        ax.grid(True, axis="y", alpha=0.3, linestyle="--")
        ax.set_axisbelow(True)

        # Add statistics text box
        avg_days = sum(holding_days) / len(holding_days)
        median_days = sorted(holding_days)[len(holding_days) // 2]
        min_days = min(holding_days)
        max_days = max(holding_days)

        stats_text = (
            f"Statistics:\n"
            f"Average: {avg_days:.1f} days\n"
            f"Median: {median_days} days\n"
            f"Min: {min_days} days\n"
            f"Max: {max_days} days\n"
            f"Total Trades: {len(holding_days)}"
        )

        ax.text(
            0.98,
            0.97,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Holding period distribution plot saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to create holding period distribution plot: {e}")


def generate_backtest_plots(result: BacktestResult, output_dir: Path) -> None:
    """
    Generate all backtest plots.

    Args:
        result: BacktestResult object
        output_dir: Directory to save plots
    """
    try:
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate cumulative P&L plot
        pnl_plot_path = output_dir / f"pnl_over_time_{timestamp}.png"
        plot_cumulative_pnl(result, pnl_plot_path)

        # Generate holding period distribution plot
        holding_plot_path = output_dir / f"holding_period_distribution_{timestamp}.png"
        plot_holding_period_distribution(result, holding_plot_path)

        logger.info(f"\nAll plots saved to: {output_dir}")

    except Exception as e:
        logger.error(f"Failed to generate plots: {e}")
