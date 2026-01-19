# Stock Market Screener & Backtester

A Python tool to screen large-cap stocks from major indices (S&P 500, DAX, FTSE 100) for companies that are at least 50 years old, headquartered in selected countries, and had the worst 5-day price performance. Includes a backtesting engine to simulate mean reversion trading strategies over historical data.

## Features

### Screening
- Screen stocks from S&P 500, DAX, and FTSE 100 indices
- Filter by company age (founding year)
- Filter by headquarters country
- Calculate worst consecutive 5-day performance using rolling window algorithm
- Export results to JSON format

### Backtesting
- Backtest mean reversion strategy over 1-5+ years
- Simulate weekly screening and trading
- Track individual trades with entry/exit prices and holding periods
- Calculate performance metrics (P&L, win rate, return %)
- Generate holding period distribution
- Support custom investment amounts and screening frequencies
- Visualize results with cumulative P&L chart and holding period histogram

### Technical
- Comprehensive error handling and retry logic for API calls
- Rate limiting to avoid being blocked by Yahoo Finance
- Timezone-aware date handling for multi-market support

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

#### Visualization

When using the `--plot` flag, two charts are generated:

1. **Cumulative P&L Over Time**: Shows how your total profit/loss accumulated throughout the backtest period
2. **Holding Period Distribution**: Histogram showing how long positions were held before exiting

Plots are saved as PNG files in the `output/` directory with timestamps.

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

### Company Metadata CSV

The tool requires a CSV file with company metadata including founding years. The CSV must have the following schema:

| Column        | Type | Required | Description                                      |
|---------------|------|----------|--------------------------------------------------|
| ticker        | str  | Yes      | Yahoo Finance ticker symbol (e.g., AAPL, SAP.DE, BP.L) |
| company_name  | str  | Yes      | Full company name                                |
| founding_year | int  | Yes      | Year company was founded (YYYY)                  |
| country       | str  | Yes      | Country of headquarters                          |
| index         | str  | Yes      | Primary index (SP500, DAX, FTSE100)              |
| notes         | str  | No       | Optional notes                                   |

**Example CSV:**

```csv
ticker,company_name,founding_year,country,index,notes
JPM,JPMorgan Chase & Co.,1799,USA,SP500,Originally founded as Bank of Manhattan Company
PG,Procter & Gamble Company,1837,USA,SP500,
SAP.DE,SAP SE,1972,Germany,DAX,
HSBA.L,HSBC Holdings plc,1865,UK,FTSE100,
```

**Note:** Companies with missing `founding_year` will be excluded from screening and backtesting.

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

Backtest results include trade-by-trade details and performance metrics:

```json
{
  "metadata": {
    "backtest_date": "2026-01-10T01:10:23.610870",
    "total_trades": 34,
    "closed_trades": 34,
    "still_open": 0,
    "winning_trades": 22,
    "losing_trades": 12,
    "total_pnl": 43.82,
    "total_invested": 1700.0,
    "return_pct": 2.58,
    "avg_holding_days": 85.1
  },
  "holding_days_distribution": {
    "0-7 days": 1,
    "7-14 days": 26,
    "14-30 days": 1,
    "90-180 days": 3,
    "180-365 days": 1,
    "365+ days": 2
  },
  "trades": [
    {
      "ticker": "KO",
      "company_name": "KO",
      "entry_date": "2021-01-11",
      "entry_price": 43.19,
      "shares": 1.1577,
      "target_price": 46.84,
      "exit_date": "2021-04-19",
      "exit_price": 46.85,
      "holding_days": 98,
      "pnl": 4.23,
      "pnl_pct": 8.47
    }
  ]
}
```

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

## How It Works

### Screening Workflow

1. **Fetch Index Constituents**: Scrape Wikipedia for S&P 500, DAX, and FTSE 100 ticker lists
2. **Load Metadata**: Load company founding years from CSV file
3. **Filter by Metadata**: Exclude companies missing founding year data
4. **Apply Filters**: Filter by minimum age and country
5. **Fetch Market Data**: Retrieve historical price data from Yahoo Finance (with rate limiting)
6. **Calculate Performance**: Find worst consecutive 5-day return using rolling window algorithm
7. **Rank & Output**: Sort by worst performance and save to JSON

### Backtesting Workflow

1. **Fetch Candidates**: Load index constituents and filter by age and country
2. **Fetch Historical Data**: Retrieve 5+ years of price history for all candidates
3. **Simulate Weekly Screenings**:
   - For each week over the backtest period:
     - Identify the stock with the worst 5-day performance (negative only)
     - Buy $50 worth at current price
     - Set target exit price to the 5-day-ago price
   - Monitor all open positions daily:
     - Close position when stock price reaches target (breakeven)
4. **Generate Report**: Calculate P&L, win rate, holding period distribution

### Worst 5-Day Performance Algorithm

The tool calculates the worst consecutive 5 trading days using a rolling window approach:

1. Fetch historical daily prices for the lookback period (default: 5 years)
2. Calculate 5-day rolling percentage returns
3. Find the minimum return (worst performance period)
4. Extract the date range, start/end prices for that period

**Example:**
If a stock dropped from $100 to $80 between March 9-13, 2020, the worst 5-day return would be -20%.

## Data Sources

### Index Constituents

- **S&P 500**: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
- **DAX**: https://en.wikipedia.org/wiki/DAX
- **FTSE 100**: https://en.wikipedia.org/wiki/FTSE_100_Index

The tool scrapes these Wikipedia pages to get current index constituents. Note that composition may lag official changes by days/weeks.

### Market Data

Market data is fetched from Yahoo Finance using the [yfinance](https://github.com/ranaroussi/yfinance) library. The tool includes:

- Retry logic with exponential backoff (3 attempts)
- Rate limiting (0.5s delay between requests)
- Comprehensive error handling

### Company Founding Dates

Founding dates must be maintained manually in `data/company_metadata.csv`. There is no reliable free API for this data. Sources for founding dates include:

- Company Wikipedia pages
- Official company websites
- Securities filings (10-K, annual reports)

## Known Limitations

### Data Quality Issues

1. **Index Constituents**
   - Wikipedia data may lag official index changes by days/weeks
   - Quarterly rebalancing not reflected in real-time
   - Ticker symbols may change due to mergers/rebranding

2. **Company Founding Dates**
   - Manual data entry required (no free API)
   - Ambiguous definitions (incorporation vs. founding vs. first trading)
   - Historical companies may have complex histories (spinoffs, mergers)

3. **Market Data (Yahoo Finance)**
   - Rate limiting (500+ stocks can take 10-30 minutes)
   - Price data may have gaps or errors
   - Some historical stocks may be delisted and unavailable
   - Different trading hours and holidays by country

4. **Worst 5-Day Calculation**
   - Finds worst consecutive 5 trading days in lookback period
   - Does not account for currency fluctuations (international stocks)
   - Different market holidays affect trading days by country
   - Requires sufficient historical data

### Technical Limitations

- **Performance**: Fetching 500+ stocks sequentially takes time (10-30 minutes)
- **Yahoo Finance blocking**: Excessive requests may result in temporary IP bans
- **CSV maintenance**: Founding dates require manual research and updates

## Extending the Tool

### Adding New Indices

To add support for additional indices:

1. Add index name to `config.SUPPORTED_INDICES` in `src/utils/config.py`
2. Implement a fetch function in `src/data/index_fetcher.py`:
   ```python
   def fetch_new_index_tickers() -> list[str]:
       # Implement Wikipedia scraping or API call
       # Add appropriate suffix for Yahoo Finance (.DE, .L, etc.)
       pass
   ```
3. Register the function in `fetch_index_tickers()` dictionary
4. Update company metadata CSV with companies from new index

### Changing Output Format

The tool currently outputs JSON. To add CSV or other formats:

1. Modify `ScreeningEngine.save_results()` in `src/screener.py`
2. Add output format parameter to CLI in `src/main.py`

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest Tests/test_screener.py -v
```

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/
```

## License

MIT License - See LICENSE file for details

## Troubleshooting

### Yahoo Finance Rate Limiting

If you encounter rate limiting errors:

1. Increase `YFINANCE_DELAY_SECONDS` in `src/utils/config.py`
2. Reduce the number of stocks by filtering more aggressively
3. Run screening in smaller batches

### Wikipedia Parsing Errors

If index fetching fails:

1. Check Wikipedia page structure hasn't changed
2. Update table parsing logic in `src/data/index_fetcher.py`
3. Use hardcoded ticker lists as fallback

### Missing Founding Data

To populate the metadata CSV:

1. Research company founding dates on Wikipedia
2. Verify with official company websites
3. Document sources in the `notes` column
4. Use incorporation date if founding date is ambiguous

## Future Enhancements

- Support for additional indices (Nikkei 225, CAC 40, etc.)
- Automated founding date lookup via web scraping
- Caching layer for market data (SQLite or Redis)
- Parallel processing for faster data fetching
- Web dashboard for visualizing results
- Additional output formats (CSV, Excel, PDF report)
- Historical screening (run analysis for past dates)
