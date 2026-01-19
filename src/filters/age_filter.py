# SPDX-FileCopyrightText: 2025 Yannick Kees
# SPDX-FileCopyrightText: 2026 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Filter companies by age."""

from datetime import datetime

import pandas as pd

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def filter_by_age(df: pd.DataFrame, min_age_years: int) -> pd.DataFrame:
    """
    Filter companies by minimum age.

    Args:
        df: DataFrame with company metadata (must have 'founding_year' column)
        min_age_years: Minimum company age in years

    Returns:
        Filtered DataFrame with only companies meeting age requirement
    """
    current_year = datetime.now().year

    original_count = len(df)

    # Calculate age and filter
    df["company_age_years"] = current_year - df["founding_year"]
    filtered_df = df[df["company_age_years"] >= min_age_years].copy()

    excluded_count = original_count - len(filtered_df)

    logger.info(
        f"Age filter (>= {min_age_years} years): {len(filtered_df)} companies passed, "
        f"{excluded_count} excluded",
    )

    return filtered_df


def get_companies_older_than(df: pd.DataFrame, founding_year: int) -> pd.DataFrame:
    """
    Get companies founded before a specific year.

    Args:
        df: DataFrame with company metadata
        founding_year: Year threshold

    Returns:
        Filtered DataFrame
    """
    return df[df["founding_year"] < founding_year].copy()


def get_companies_in_age_range(df: pd.DataFrame, min_age: int, max_age: int) -> pd.DataFrame:
    """
    Get companies within an age range.

    Args:
        df: DataFrame with company metadata
        min_age: Minimum age in years
        max_age: Maximum age in years

    Returns:
        Filtered DataFrame
    """
    current_year = datetime.now().year

    df["company_age_years"] = current_year - df["founding_year"]

    return df[(df["company_age_years"] >= min_age) & (df["company_age_years"] <= max_age)].copy()
