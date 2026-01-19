# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Main stock screening orchestration logic."""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .data import company_metadata, index_fetcher, market_data
from .filters import age_filter, country_filter, performance_filter
from .models.schemas import ScreeningMetadata, ScreeningOutput, ScreeningResult
from .utils.config import config
from .utils.logger import setup_logger

logger = setup_logger(__name__)


class ScreeningEngine:
    """Orchestrates the stock screening workflow."""

    def __init__(
        self,
        indices: list[str],
        min_age_years: int,
        countries: list[str] | None = None,
        metadata_path: Path | None = None,
        lookback_days: int | None = None,
    ):
        """
        Initialize screening engine.

        Args:
            indices: List of index names (e.g., ['SP500', 'DAX'])
            min_age_years: Minimum company age in years
            countries: List of countries to filter (None = all)
            metadata_path: Path to metadata CSV (None = use default)
            lookback_days: Days to analyze for performance (None = use default)
        """
        self.indices = indices
        self.min_age_years = min_age_years
        self.countries = countries or []
        self.metadata_path = metadata_path or config.METADATA_CSV
        self.lookback_days = lookback_days or config.LOOKBACK_DAYS

        self.warnings: list[str] = []

    def run(self) -> ScreeningOutput:
        """
        Execute the screening workflow.

        Returns:
            ScreeningOutput with results and metadata
        """
        logger.info("=" * 80)
        logger.info("Starting stock screening workflow")
        logger.info("=" * 80)
        logger.info(f"Indices: {', '.join(self.indices)}")
        logger.info(f"Min age: {self.min_age_years} years")
        logger.info(f"Countries: {self.countries or 'all'}")
        logger.info(f"Lookback period: {self.lookback_days} days")
        logger.info("=" * 80)

        # Step 1: Fetch index constituents
        logger.info("\n[Step 1/6] Fetching index constituents...")
        all_tickers = self._fetch_index_constituents()

        # Step 2: Load company metadata
        logger.info("\n[Step 2/6] Loading company metadata...")
        metadata_df = self._load_metadata()

        # Step 3: Filter by available metadata
        logger.info("\n[Step 3/6] Filtering by available metadata...")
        filtered_df, total_candidates, excluded_no_metadata = self._filter_by_metadata(
            all_tickers, metadata_df
        )

        # Step 4: Apply age and country filters
        logger.info("\n[Step 4/6] Applying age and country filters...")
        filtered_df, excluded_too_young = self._apply_filters(filtered_df)

        if len(filtered_df) == 0:
            logger.warning("No companies passed all filters!")
            return self._create_empty_output(
                total_candidates, excluded_no_metadata, excluded_too_young
            )

        # Step 5: Fetch market data
        logger.info("\n[Step 5/6] Fetching market data...")
        market_data_dict = self._fetch_market_data(filtered_df)

        # Step 6: Calculate performance and rank
        logger.info("\n[Step 6/6] Calculating performance and ranking...")
        results = self._calculate_and_rank(filtered_df, market_data_dict)

        # Create output
        output = self._create_output(
            results,
            total_candidates,
            len(metadata_df),
            len(results),
            excluded_no_metadata,
            excluded_too_young,
        )

        logger.info("=" * 80)
        logger.info(f"Screening complete! Found {len(results)} qualifying companies")
        logger.info("=" * 80)

        return output

    def _fetch_index_constituents(self) -> list[str]:
        """Fetch all tickers from selected indices."""
        all_tickers = []

        for index_name in self.indices:
            try:
                tickers = index_fetcher.fetch_index_tickers(index_name)
                all_tickers.extend(tickers)
                logger.info(f"  {index_name}: {len(tickers)} tickers")
            except Exception as e:
                logger.error(f"  Failed to fetch {index_name}: {e}")
                self.warnings.append(f"Failed to fetch {index_name} constituents")

        logger.info(f"\nTotal tickers from all indices: {len(all_tickers)}")
        return all_tickers

    def _load_metadata(self) -> pd.DataFrame:
        """Load company metadata from CSV."""
        try:
            metadata_df = company_metadata.load_metadata(self.metadata_path)
            logger.info(f"Loaded metadata for {len(metadata_df)} companies")
            return metadata_df
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            raise

    def _filter_by_metadata(
        self, all_tickers: list[str], metadata_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, int, int]:
        """Filter tickers to only those with metadata."""
        total_candidates = len(all_tickers)

        # Get companies that are in both index and metadata
        filtered_df = company_metadata.get_companies_by_tickers(metadata_df, all_tickers)

        excluded_no_metadata = total_candidates - len(filtered_df)

        logger.info(
            f"Companies with metadata: {len(filtered_df)}/{total_candidates} "
            f"({excluded_no_metadata} excluded)"
        )

        if excluded_no_metadata > 0:
            self.warnings.append(
                f"{excluded_no_metadata} companies excluded due to missing founding data in CSV"
            )

        return filtered_df, total_candidates, excluded_no_metadata

    def _apply_filters(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """Apply age and country filters."""
        original_count = len(df)

        # Age filter
        df = age_filter.filter_by_age(df, self.min_age_years)

        excluded_too_young = original_count - len(df)

        # Country filter (if specified)
        if self.countries:
            df = country_filter.filter_by_country(df, self.countries)

        logger.info(f"Companies after filters: {len(df)}")

        return df, excluded_too_young

    def _fetch_market_data(self, df: pd.DataFrame) -> dict:
        """Fetch market data for all filtered companies."""
        tickers = df["ticker"].tolist()

        market_data_dict = market_data.fetch_multiple_stocks(
            tickers, lookback_days=self.lookback_days
        )

        failed_count = len(tickers) - len(market_data_dict)
        if failed_count > 0:
            self.warnings.append(
                f"{failed_count} tickers failed to fetch from Yahoo Finance (rate limited or delisted)"
            )

        return market_data_dict

    def _calculate_and_rank(
        self, df: pd.DataFrame, market_data_dict: dict
    ) -> list[ScreeningResult]:
        """Calculate performance and create ranked results."""
        # Calculate worst 5-day performance for all stocks
        performance_data = performance_filter.calculate_performance_for_multiple(market_data_dict)

        # Rank by worst performance
        ranked = performance_filter.rank_by_worst_performance(performance_data)

        # Create ScreeningResult objects
        results = []
        for ticker, perf in ranked:
            company = company_metadata.get_company(df, ticker)
            if company:
                result = ScreeningResult(
                    ticker=company.ticker,
                    company_name=company.company_name,
                    country=company.country,
                    index=company.index,
                    founding_year=company.founding_year,
                    company_age_years=company.company_age_years,
                    worst_5day_performance=perf,
                )
                results.append(result)

        return results

    def _create_output(
        self,
        results: list[ScreeningResult],
        total_candidates: int,
        companies_with_metadata: int,
        companies_screened: int,
        excluded_no_metadata: int,
        excluded_too_young: int,
    ) -> ScreeningOutput:
        """Create final output structure."""
        metadata = ScreeningMetadata(
            screening_date=datetime.now().isoformat(),
            filters_applied={
                "indices": self.indices,
                "countries": self.countries if self.countries else ["all"],
                "min_age_years": self.min_age_years,
                "lookback_days": self.lookback_days,
            },
            total_candidates=total_candidates,
            companies_with_metadata=companies_with_metadata,
            companies_screened=companies_screened,
            excluded_no_metadata=excluded_no_metadata,
            excluded_too_young=excluded_too_young,
        )

        return ScreeningOutput(metadata=metadata, results=results, warnings=self.warnings)

    def _create_empty_output(
        self, total_candidates: int, excluded_no_metadata: int, excluded_too_young: int
    ) -> ScreeningOutput:
        """Create output when no results found."""
        metadata = ScreeningMetadata(
            screening_date=datetime.now().isoformat(),
            filters_applied={
                "indices": self.indices,
                "countries": self.countries if self.countries else ["all"],
                "min_age_years": self.min_age_years,
                "lookback_days": self.lookback_days,
            },
            total_candidates=total_candidates,
            companies_with_metadata=0,
            companies_screened=0,
            excluded_no_metadata=excluded_no_metadata,
            excluded_too_young=excluded_too_young,
        )

        return ScreeningOutput(metadata=metadata, results=[], warnings=self.warnings)

    def save_results(self, output: ScreeningOutput, output_path: Path) -> None:
        """
        Save screening results to JSON file.

        Args:
            output: ScreeningOutput object
            output_path: Path to save JSON file
        """
        try:
            # Convert to dict
            output_dict = output.model_dump()

            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(output_dict, f, indent=2)

            logger.info(f"\nResults saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
