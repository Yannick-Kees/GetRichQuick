# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Load and validate company metadata from CSV."""
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..models.schemas import Company
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def load_metadata(csv_path: Path) -> pd.DataFrame:
    """
    Load company metadata from CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        DataFrame with validated company metadata

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV is missing required columns or has invalid data
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Metadata CSV not found: {csv_path}")

    logger.info(f"Loading metadata from {csv_path}")

    try:
        df = pd.read_csv(csv_path)

        # Validate required columns
        required_columns = ["ticker", "company_name", "founding_year", "country", "index"]
        missing_columns = set(required_columns) - set(df.columns)

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Remove rows with missing founding_year (NaN)
        original_count = len(df)
        df = df.dropna(subset=["founding_year"])
        removed_count = original_count - len(df)

        if removed_count > 0:
            logger.warning(
                f"Removed {removed_count} companies with missing founding_year data"
            )

        # Convert founding_year to int
        df["founding_year"] = df["founding_year"].astype(int)

        # Validate each row using Pydantic model
        invalid_rows = []
        current_year = datetime.now().year

        for idx, row in df.iterrows():
            try:
                # Validate founding year range
                if not 1600 <= row["founding_year"] <= current_year:
                    invalid_rows.append(
                        (idx, f"Invalid founding year: {row['founding_year']}")
                    )
                    continue

                # Validate index
                if row["index"] not in {"SP500", "DAX", "FTSE100"}:
                    invalid_rows.append((idx, f"Invalid index: {row['index']}"))
                    continue

            except Exception as e:
                invalid_rows.append((idx, str(e)))

        # Remove invalid rows
        if invalid_rows:
            logger.warning(f"Found {len(invalid_rows)} invalid rows:")
            for idx, reason in invalid_rows:
                logger.warning(f"  Row {idx}: {reason}")

            df = df.drop([idx for idx, _ in invalid_rows])

        logger.info(f"Successfully loaded {len(df)} companies from metadata")

        return df

    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        raise


def get_companies_by_index(df: pd.DataFrame, index_name: str) -> pd.DataFrame:
    """
    Filter companies by index.

    Args:
        df: DataFrame with company metadata
        index_name: Index name (SP500, DAX, FTSE100)

    Returns:
        Filtered DataFrame
    """
    return df[df["index"] == index_name].copy()


def get_companies_by_country(df: pd.DataFrame, countries: list[str]) -> pd.DataFrame:
    """
    Filter companies by country.

    Args:
        df: DataFrame with company metadata
        countries: List of country names

    Returns:
        Filtered DataFrame
    """
    return df[df["country"].isin(countries)].copy()


def get_companies_by_tickers(df: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """
    Filter companies by ticker symbols.

    Args:
        df: DataFrame with company metadata
        tickers: List of ticker symbols

    Returns:
        Filtered DataFrame with only matching tickers
    """
    return df[df["ticker"].isin(tickers)].copy()


def get_company(df: pd.DataFrame, ticker: str) -> Company | None:
    """
    Get a single company by ticker.

    Args:
        df: DataFrame with company metadata
        ticker: Ticker symbol

    Returns:
        Company object or None if not found
    """
    row = df[df["ticker"] == ticker]

    if row.empty:
        return None

    row_dict = row.iloc[0].to_dict()

    return Company(
        ticker=row_dict["ticker"],
        company_name=row_dict["company_name"],
        founding_year=int(row_dict["founding_year"]),
        country=row_dict["country"],
        index=row_dict["index"],
        notes=row_dict.get("notes"),
    )
