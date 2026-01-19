# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Filter companies by country."""
import pandas as pd

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def filter_by_country(df: pd.DataFrame, countries: list[str] | None = None) -> pd.DataFrame:
    """
    Filter companies by country of headquarters.

    Args:
        df: DataFrame with company metadata (must have 'country' column)
        countries: List of country names to include (None = all countries)

    Returns:
        Filtered DataFrame
    """
    if countries is None or len(countries) == 0:
        logger.info("No country filter applied (all countries included)")
        return df.copy()

    original_count = len(df)

    # Normalize country names to uppercase for case-insensitive matching
    countries_normalized = [c.upper() for c in countries]
    df_normalized = df.copy()
    df_normalized["country_upper"] = df_normalized["country"].str.upper()

    filtered_df = df[df_normalized["country_upper"].isin(countries_normalized)].copy()

    excluded_count = original_count - len(filtered_df)

    logger.info(
        f"Country filter ({', '.join(countries)}): {len(filtered_df)} companies passed, "
        f"{excluded_count} excluded"
    )

    return filtered_df


def get_countries(df: pd.DataFrame) -> list[str]:
    """
    Get list of unique countries in the dataset.

    Args:
        df: DataFrame with company metadata

    Returns:
        Sorted list of unique country names
    """
    return sorted(df["country"].unique().tolist())


def get_companies_count_by_country(df: pd.DataFrame) -> dict[str, int]:
    """
    Get count of companies per country.

    Args:
        df: DataFrame with company metadata

    Returns:
        Dictionary mapping country name to count
    """
    return df["country"].value_counts().to_dict()
