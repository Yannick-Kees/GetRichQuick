# Stock Market Screener & Backtester

A Python tool to screen large-cap stocks from major indices (S&P 500, DAX, FTSE 100) for companies that are at least 50 years old, headquartered in selected countries, and had the worst 5-day price performance. Includes a backtesting engine to simulate mean reversion trading strategies over historical data.


## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

```bash
# Install dependencies
uv sync

# Or if you don't have uv installed
pip install uv
uv sync
```

**Key Dependencies:**
- `yfinance` - Yahoo Finance API for market data
- `pandas` - Data manipulation
- `matplotlib` - Plotting and visualization
- `pydantic` - Data validation
- `click` - CLI framework

## Quick Start

```bash
# Screen all indices with default settings (50+ years old)
uv run python -m src.main screen

# Screen S&P 500 for US companies at least 50 years old
uv run python -m src.main screen --index SP500 --country USA --min-age 50

# Screen DAX and FTSE 100 for German and UK companies at least 100 years old
uv run python -m src.main screen --index DAX --index FTSE100 --country Germany --country UK --min-age 100

# Backtest mean reversion strategy for 5 years on US companies
uv run python -m src.main backtest --index SP500 --country USA --lookback-years 5

# Backtest with plots
uv run python -m src.main backtest --index SP500 --country USA --lookback-years 5 --plot

# Enable verbose logging
uv run python -m src.main screen --index SP500 --country USA --verbose
```

## Usage

The tool has two main commands: `screen` and `backtest`.

### Screening Command

Screen stocks for worst 5-day performance:

```bash
uv run python -m src.main screen [OPTIONS]

Options:
  --index, -i [SP500|DAX|FTSE100]  Index to screen (can specify multiple times). Default: all indices.
  --min-age INTEGER                Minimum company age in years (default: 50)
  --country, -c TEXT               Filter by country (can specify multiple times). Default: all countries.
  --metadata PATH                  Path to company metadata CSV (default: data/company_metadata.csv)
  --output, -o PATH                Output JSON file path (default: output/screening_results_<timestamp>.json)
  --lookback-days INTEGER          Days of historical data to analyze (default: 1825 ~5 years)
  --verbose, -v                    Enable verbose logging (DEBUG level)
  --help                           Show this message and exit.
```

### Backtesting Command

Backtest a mean reversion strategy over historical data:

```bash
uv run python -m src.main backtest [OPTIONS]

Options:
  --index, -i [SP500|DAX|FTSE100]  Index to backtest (can specify multiple times). Default: all indices.
  --min-age INTEGER                Minimum company age in years (default: 50)
  --country, -c TEXT               Filter by country (can specify multiple times). Default: all countries.
  --metadata PATH                  Path to company metadata CSV (default: data/company_metadata.csv)
  --output, -o PATH                Output JSON file path (default: output/backtest_results_<timestamp>.json)
  --lookback-years INTEGER         Years to backtest (default: 5)
  --investment FLOAT               Investment amount per trade in $ (default: 50)
  --frequency-days INTEGER         Days between screening runs (default: 7 = weekly)
  --plot, -p                       Generate plots (cumulative P&L and holding period distribution)
  --verbose, -v                    Enable verbose logging (DEBUG level)
  --help                           Show this message and exit.
```




#### Backtesting Strategy

The backtest simulates a mean reversion trading strategy:

1. **Weekly Screening**: Run the screener every 7 days (configurable)
2. **Entry Condition**: Buy $50 (configurable) worth of the stock with the worst 5-day performance (only if negative)
3. **Exit Condition**: Sell when the stock recovers to its price from 5 days ago (breakeven point)
4. **Position Limit**: Only one position per stock at a time

**Example Results** (5-year backtest on S&P 500 US companies 100+ years old):
- Total trades: 34
- Win rate: 64.7% (22 winners, 12 losers)
- Total P&L: $43.82 on $1,700 invested (2.58% return)
- Average holding period: 85.1 days
- Most trades (76.5%) held for 7-14 days



### Output Format

#### Screening Output

Screening results are saved as JSON with the following structure:

```json
{
  "metadata": {
    "screening_date": "2026-01-10T12:00:00Z",
    "filters_applied": {
      "indices": ["SP500", "DAX"],
      "countries": ["USA", "Germany"],
      "min_age_years": 50,
      "lookback_days": 1825
    },
    "total_candidates": 540,
    "companies_with_metadata": 412,
    "companies_screened": 89,
    "excluded_no_metadata": 128,
    "excluded_too_young": 323
  },
  "results": [
    {
      "ticker": "BP.L",
      "company_name": "BP plc",
      "country": "UK",
      "index": "FTSE100",
      "founding_year": 1909,
      "company_age_years": 117,
      "worst_5day_performance": {
        "return_pct": -23.45,
        "start_date": "2020-03-09",
        "end_date": "2020-03-13",
        "start_price": 385.50,
        "end_price": 295.10
      }
    }
  ],
  "warnings": [
    "128 companies excluded due to missing founding data in CSV",
    "7 tickers failed to fetch from Yahoo Finance (rate limited or delisted)"
  ]
}
```

#### Backtesting Output

Backtest results include trade-by-trade details and performance metrics.

## Architecture

The tool is organized into modular components:

```
src/
├── main.py                      # CLI entry point (screen & backtest commands)
├── screener.py                  # Screening orchestration logic
├── backtesting/
│   ├── engine.py                # Backtesting simulation engine
│   └── reporter.py              # Backtest report generation
├── data/
│   ├── index_fetcher.py         # Fetch index constituents from Wikipedia
│   ├── company_metadata.py      # Load/validate CSV metadata
│   └── market_data.py           # Fetch market data via yfinance
├── filters/
│   ├── age_filter.py            # Filter by company age
│   ├── country_filter.py        # Filter by country
│   └── performance_filter.py    # Calculate worst 5-day performance
├── models/
│   └── schemas.py               # Pydantic data models
└── utils/
    ├── config.py                # Configuration settings
    └── logger.py                # Logging setup
```

