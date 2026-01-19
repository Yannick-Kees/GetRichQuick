# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Calculate and filter by stock performance."""
import pandas as pd

from ..models.schemas import WorstPerformance
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def calculate_worst_5day_performance(hist: pd.DataFrame) -> WorstPerformance | None:
    """
    Calculate worst consecutive 5-day performance using rolling window.

    Args:
        hist: Historical price DataFrame from yfinance (must have 'Close' column)

    Returns:
        WorstPerformance object with details, or None if insufficient data

    Algorithm:
        1. Calculate 5-day rolling percentage return
        2. Find the minimum return (worst performance)
        3. Extract date range and prices for that period
    """
    try:
        if len(hist) < 5:
            logger.warning("Insufficient data for 5-day performance calculation")
            return None

        # Calculate 5-day percentage change (from 5 days ago to today)
        hist = hist.copy()
        hist["5d_pct_change"] = hist["Close"].pct_change(periods=5) * 100

        # Remove NaN values (first 5 days)
        hist_valid = hist.dropna(subset=["5d_pct_change"])

        if len(hist_valid) == 0:
            logger.warning("No valid 5-day returns calculated")
            return None

        # Find the worst performance (minimum return)
        worst_idx = hist_valid["5d_pct_change"].idxmin()
        worst_return = hist_valid.loc[worst_idx, "5d_pct_change"]

        # Get the end date (date of worst_idx)
        end_date = worst_idx

        # Get the start date (5 trading days before worst_idx)
        # Find the index position
        idx_position = hist.index.get_loc(worst_idx)

        # Look back 5 positions (5 trading days)
        if idx_position < 5:
            logger.warning("Cannot look back 5 days from worst performance date")
            return None

        start_idx_position = idx_position - 5
        start_date = hist.index[start_idx_position]

        # Get prices
        start_price = hist.loc[start_date, "Close"]
        end_price = hist.loc[end_date, "Close"]

        return WorstPerformance(
            return_pct=round(worst_return, 2),
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            start_price=round(float(start_price), 2),
            end_price=round(float(end_price), 2),
        )

    except Exception as e:
        logger.error(f"Error calculating worst 5-day performance: {e}")
        return None


def calculate_performance_for_multiple(
    market_data: dict[str, pd.DataFrame]
) -> dict[str, WorstPerformance]:
    """
    Calculate worst 5-day performance for multiple stocks.

    Args:
        market_data: Dictionary mapping ticker to historical DataFrame

    Returns:
        Dictionary mapping ticker to WorstPerformance (excludes failed calculations)
    """
    results = {}

    logger.info(f"Calculating worst 5-day performance for {len(market_data)} stocks")

    for ticker, hist in market_data.items():
        try:
            performance = calculate_worst_5day_performance(hist)

            if performance is not None:
                results[ticker] = performance
            else:
                logger.warning(f"Could not calculate performance for {ticker}")

        except Exception as e:
            logger.error(f"Failed to calculate performance for {ticker}: {e}")
            continue

    logger.info(
        f"Successfully calculated performance for {len(results)}/{len(market_data)} stocks"
    )

    return results


def rank_by_worst_performance(
    performance_data: dict[str, WorstPerformance]
) -> list[tuple[str, WorstPerformance]]:
    """
    Rank stocks by worst performance (most negative first).

    Args:
        performance_data: Dictionary mapping ticker to WorstPerformance

    Returns:
        List of (ticker, performance) tuples sorted by worst performance
    """
    # Sort by return_pct ascending (most negative first)
    ranked = sorted(performance_data.items(), key=lambda x: x[1].return_pct)

    logger.info(
        f"Ranked {len(ranked)} stocks by worst performance "
        f"(worst: {ranked[0][1].return_pct:.2f}%)"
    )

    return ranked


def get_top_n_worst_performers(
    performance_data: dict[str, WorstPerformance], n: int
) -> list[tuple[str, WorstPerformance]]:
    """
    Get top N worst performing stocks.

    Args:
        performance_data: Dictionary mapping ticker to WorstPerformance
        n: Number of results to return

    Returns:
        List of (ticker, performance) tuples for top N worst performers
    """
    ranked = rank_by_worst_performance(performance_data)
    return ranked[:n]
