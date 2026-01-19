# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Application configuration."""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration settings."""

    # Paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    METADATA_CSV: Path = DATA_DIR / "company_metadata.csv"

    # Screening defaults
    MIN_AGE_YEARS: int = 50
    LOOKBACK_DAYS: int = 1825  # ~5 years

    # API settings
    YFINANCE_DELAY_SECONDS: float = 0.5  # Rate limiting between requests
    RETRY_ATTEMPTS: int = 3
    RETRY_MIN_WAIT: int = 2  # seconds
    RETRY_MAX_WAIT: int = 10  # seconds

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Supported indices
    SUPPORTED_INDICES: set[str] = frozenset({"SP500", "DAX", "FTSE100"})

    def __post_init__(self):
        """Ensure directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = Config()
