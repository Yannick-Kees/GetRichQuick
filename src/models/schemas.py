# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Pydantic models for type safety and data validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Company(BaseModel):
    """Represents a company with metadata."""

    ticker: str = Field(..., description="Yahoo Finance ticker symbol")
    company_name: str = Field(..., description="Full company name")
    founding_year: int = Field(..., description="Year company was founded")
    country: str = Field(..., description="Country of headquarters")
    index: str = Field(..., description="Primary index (SP500, DAX, FTSE100)")
    notes: Optional[str] = Field(None, description="Optional notes")

    @field_validator("founding_year")
    @classmethod
    def validate_founding_year(cls, v: int) -> int:
        """Validate founding year is reasonable."""
        if not 1600 <= v <= datetime.now().year:
            raise ValueError(f"Founding year must be between 1600 and {datetime.now().year}")
        return v

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: str) -> str:
        """Validate index is one of the supported indices."""
        valid_indices = {"SP500", "DAX", "FTSE100"}
        if v not in valid_indices:
            raise ValueError(f"Index must be one of {valid_indices}")
        return v

    @property
    def company_age_years(self) -> int:
        """Calculate company age in years."""
        return datetime.now().year - self.founding_year


class WorstPerformance(BaseModel):
    """Represents worst 5-day performance data."""

    return_pct: float = Field(..., description="Percentage return over 5 days")
    start_date: str = Field(..., description="Start date of worst period (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date of worst period (YYYY-MM-DD)")
    start_price: float = Field(..., description="Price at start of period")
    end_price: float = Field(..., description="Price at end of period")


class ScreeningResult(BaseModel):
    """Represents a single screening result."""

    ticker: str
    company_name: str
    country: str
    index: str
    founding_year: int
    company_age_years: int
    worst_5day_performance: WorstPerformance


class ScreeningMetadata(BaseModel):
    """Metadata about the screening run."""

    screening_date: str = Field(..., description="ISO timestamp of screening")
    filters_applied: dict = Field(..., description="Filters applied during screening")
    total_candidates: int = Field(..., description="Total tickers in selected indices")
    companies_with_metadata: int = Field(
        ..., description="Companies with founding data in CSV"
    )
    companies_screened: int = Field(..., description="Companies that passed all filters")
    excluded_no_metadata: int = Field(
        ..., description="Companies excluded due to missing metadata"
    )
    excluded_too_young: int = Field(..., description="Companies excluded due to age filter")


class ScreeningOutput(BaseModel):
    """Complete screening output structure."""

    metadata: ScreeningMetadata
    results: list[ScreeningResult]
    warnings: list[str]
