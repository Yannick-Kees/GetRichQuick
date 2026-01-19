# SPDX-FileCopyrightText: 2025 Yannick Kees
# SPDX-FileCopyrightText: 2026 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Fetch index constituents from Wikipedia."""

import pandas as pd

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def fetch_sp500_tickers() -> list[str]:
    """
    Fetch S&P 500 constituents from Wikipedia.

    Returns:
        List of ticker symbols

    Raises:
        Exception: If fetching or parsing fails
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        logger.info(f"Fetching S&P 500 constituents from {url}")

        # Add headers to avoid 403 Forbidden
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        tables = pd.read_html(url, storage_options=headers)
        df = tables[0]  # First table contains current constituents

        tickers = df["Symbol"].tolist()
        logger.info(f"Successfully fetched {len(tickers)} S&P 500 tickers")

        return tickers

    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 tickers: {e}")
        raise


def fetch_dax_tickers() -> list[str]:
    """
    Fetch DAX constituents from Wikipedia.

    Returns:
        List of ticker symbols with .DE suffix for Yahoo Finance

    Raises:
        Exception: If fetching or parsing fails
    """
    try:
        url = "https://en.wikipedia.org/wiki/DAX"
        logger.info(f"Fetching DAX constituents from {url}")

        # Add headers to avoid 403 Forbidden
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        tables = pd.read_html(url, storage_options=headers)

        # Find the table with constituents (usually has 'Ticker' or 'Company' column)
        df = None
        for table in tables:
            if "Ticker" in table.columns or "Company" in table.columns:
                df = table
                break

        if df is None:
            raise ValueError("Could not find DAX constituents table")

        # Extract ticker column
        if "Ticker" in df.columns:
            tickers = df["Ticker"].tolist()
        elif "Company" in df.columns:
            # Some tables have ticker in different column
            tickers = df.iloc[:, 1].tolist()  # Usually second column
        else:
            raise ValueError("Could not identify ticker column")

        # Add .DE suffix for Yahoo Finance
        tickers = [f"{ticker}.DE" for ticker in tickers if pd.notna(ticker)]

        logger.info(f"Successfully fetched {len(tickers)} DAX tickers")

        return tickers

    except Exception as e:
        logger.error(f"Failed to fetch DAX tickers: {e}")
        raise


def fetch_ftse100_tickers() -> list[str]:
    """
    Fetch FTSE 100 constituents from Wikipedia.

    Returns:
        List of ticker symbols with .L suffix for Yahoo Finance

    Raises:
        Exception: If fetching or parsing fails
    """
    try:
        url = "https://en.wikipedia.org/wiki/FTSE_100_Index"
        logger.info(f"Fetching FTSE 100 constituents from {url}")

        # Add headers to avoid 403 Forbidden
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        tables = pd.read_html(url, storage_options=headers)

        # Find the table with constituents
        df = None
        for table in tables:
            if "Ticker" in table.columns or "EPIC" in table.columns or "Company" in table.columns:
                df = table
                break

        if df is None:
            raise ValueError("Could not find FTSE 100 constituents table")

        # Extract ticker column (might be 'Ticker' or 'EPIC')
        if "Ticker" in df.columns:
            tickers = df["Ticker"].tolist()
        elif "EPIC" in df.columns:
            tickers = df["EPIC"].tolist()
        elif "Company" in df.columns:
            # Some tables have ticker in different column
            tickers = df.iloc[:, 1].tolist()
        else:
            raise ValueError("Could not identify ticker column")

        # Add .L suffix for Yahoo Finance (London Stock Exchange)
        tickers = [f"{ticker}.L" for ticker in tickers if pd.notna(ticker)]

        logger.info(f"Successfully fetched {len(tickers)} FTSE 100 tickers")

        return tickers

    except Exception as e:
        logger.error(f"Failed to fetch FTSE 100 tickers: {e}")
        raise


def fetch_index_tickers(index_name: str) -> list[str]:
    """
    Fetch tickers for a specific index.

    Args:
        index_name: Index name (SP500, DAX, or FTSE100)

    Returns:
        List of ticker symbols

    Raises:
        ValueError: If index name is not supported
        Exception: If fetching fails
    """
    index_fetchers = {
        "SP500": fetch_sp500_tickers,
        "DAX": fetch_dax_tickers,
        "FTSE100": fetch_ftse100_tickers,
    }

    if index_name not in index_fetchers:
        raise ValueError(
            f"Unsupported index: {index_name} " f"Supported indices: {list(index_fetchers.keys())}",
        )

    return index_fetchers[index_name]()


def fetch_all_indices(indices: list[str]) -> dict[str, list[str]]:
    """
    Fetch tickers for multiple indices.

    Args:
        indices: List of index names (e.g., ['SP500', 'DAX'])

    Returns:
        Dictionary mapping index name to list of tickers

    Raises:
        ValueError: If any index name is not supported
    """
    results = {}

    for index_name in indices:
        try:
            tickers = fetch_index_tickers(index_name)
            results[index_name] = tickers
        except Exception as e:
            logger.error(f"Failed to fetch {index_name}: {e}")
            results[index_name] = []

    return results
