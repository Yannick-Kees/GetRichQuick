# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Fetch market data using yfinance with retry logic."""
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@retry(
    stop=stop_after_attempt(config.RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=1, min=config.RETRY_MIN_WAIT, max=config.RETRY_MAX_WAIT
    ),
)
def fetch_stock_history(ticker: str, lookback_days: int = 1825) -> pd.DataFrame:
    """
    Fetch historical stock data with automatic retry on failure.

    Args:
        ticker: Stock ticker symbol
        lookback_days: Number of days to look back (default: ~5 years)

    Returns:
        DataFrame with historical price data (Date, Open, High, Low, Close, Volume)

    Raises:
        ValueError: If no data is returned
        Exception: If fetching fails after retries
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        logger.debug(
            f"Fetching data for {ticker} from {start_date.date()} to {end_date.date()}"
        )

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            raise ValueError(f"No data returned for {ticker}")

        logger.debug(f"Successfully fetched {len(hist)} days of data for {ticker}")

        return hist

    except Exception as e:
        logger.warning(f"Failed to fetch data for {ticker}: {e}")
        raise


def fetch_multiple_stocks(
    tickers: list[str], lookback_days: int = 1825, rate_limit: bool = True
) -> dict[str, pd.DataFrame]:
    """
    Fetch historical data for multiple stocks with rate limiting.

    Args:
        tickers: List of ticker symbols
        lookback_days: Number of days to look back
        rate_limit: Whether to apply rate limiting (default: True)

    Returns:
        Dictionary mapping ticker to DataFrame (excludes failed tickers)
    """
    results = {}
    total = len(tickers)

    logger.info(f"Fetching market data for {total} tickers (rate limit: {rate_limit})")

    for i, ticker in enumerate(tickers, 1):
        try:
            logger.info(f"Fetching {ticker} ({i}/{total})")

            hist = fetch_stock_history(ticker, lookback_days)
            results[ticker] = hist

            # Rate limiting to avoid being blocked
            if rate_limit and i < total:
                time.sleep(config.YFINANCE_DELAY_SECONDS)

        except Exception as e:
            logger.error(f"Failed to fetch {ticker} after retries: {e}")
            continue

    logger.info(
        f"Successfully fetched {len(results)}/{total} stocks "
        f"({total - len(results)} failed)"
    )

    return results


def calculate_return(start_price: float, end_price: float) -> float:
    """
    Calculate percentage return.

    Args:
        start_price: Starting price
        end_price: Ending price

    Returns:
        Percentage return (e.g., -15.5 for -15.5%)
    """
    return ((end_price - start_price) / start_price) * 100


def get_price_on_date(hist: pd.DataFrame, date: datetime) -> float | None:
    """
    Get closing price on a specific date.

    Args:
        hist: Historical price DataFrame
        date: Date to look up

    Returns:
        Closing price or None if date not found
    """
    try:
        # Handle timezone-aware datetime comparison
        if hist.index.tz is not None:
            # Convert date to timezone-aware
            date_tz = pd.Timestamp(date).tz_localize(hist.index.tz)
        else:
            date_tz = date

        return hist.loc[date_tz, "Close"]
    except KeyError:
        # Date not in index (weekend, holiday, etc.)
        # Find nearest prior date
        if hist.index.tz is not None:
            date_tz = pd.Timestamp(date).tz_localize(hist.index.tz)
        else:
            date_tz = date

        prior_dates = hist.index[hist.index <= date_tz]
        if len(prior_dates) > 0:
            return hist.loc[prior_dates[-1], "Close"]
        return None
