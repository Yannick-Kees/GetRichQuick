# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Stock screening CLI application."""
from datetime import datetime
from pathlib import Path

import click

from .screener import ScreeningEngine
from .utils.config import config
from .utils.logger import setup_logger

logger = setup_logger(__name__)


@click.group()
def cli():
    """Stock Market Screener and Backtester."""
    pass


@cli.command()
@click.option(
    "--index",
    "-i",
    "indices",
    multiple=True,
    type=click.Choice(["SP500", "DAX", "FTSE100"], case_sensitive=False),
    help="Index to screen (can specify multiple times). Default: all indices.",
)
@click.option(
    "--min-age",
    type=int,
    default=config.MIN_AGE_YEARS,
    help=f"Minimum company age in years (default: {config.MIN_AGE_YEARS})",
)
@click.option(
    "--country",
    "-c",
    "countries",
    multiple=True,
    help="Filter by country (can specify multiple times). Default: all countries.",
)
@click.option(
    "--metadata",
    type=click.Path(exists=True, path_type=Path),
    default=config.METADATA_CSV,
    help=f"Path to company metadata CSV (default: {config.METADATA_CSV})",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file path (default: output/screening_results_<timestamp>.json)",
)
@click.option(
    "--lookback-days",
    type=int,
    default=config.LOOKBACK_DAYS,
    help=f"Days of historical data to analyze (default: {config.LOOKBACK_DAYS})",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
def screen(
    indices: tuple[str, ...],
    min_age: int,
    countries: tuple[str, ...],
    metadata: Path,
    output: Path | None,
    lookback_days: int,
    verbose: bool,
):
    """
    Screen large-cap stocks for old companies with worst 5-day performance.

    Examples:

      # Screen S&P 500 for US companies at least 50 years old
      uv run src/main.py --index SP500 --country USA --min-age 50

      # Screen all indices with default settings
      uv run src/main.py

      # Screen DAX and FTSE 100 for companies at least 100 years old
      uv run src/main.py --index DAX --index FTSE100 --min-age 100
    """
    # Set log level
    if verbose:
        logger.setLevel("DEBUG")

    # Default to all indices if none specified
    if not indices:
        indices = list(config.SUPPORTED_INDICES)
    else:
        indices = [idx.upper() for idx in indices]

    # Convert countries to list
    countries_list = list(countries) if countries else []

    # Generate default output path if not specified
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = config.OUTPUT_DIR / f"screening_results_{timestamp}.json"

    try:
        # Create screening engine
        engine = ScreeningEngine(
            indices=indices,
            min_age_years=min_age,
            countries=countries_list,
            metadata_path=metadata,
            lookback_days=lookback_days,
        )

        # Run screening
        results = engine.run()

        # Save results
        engine.save_results(results, output)

        # Print summary
        click.echo("\n" + "=" * 80)
        click.echo("SCREENING SUMMARY")
        click.echo("=" * 80)
        click.echo(f"Total candidates: {results.metadata.total_candidates}")
        click.echo(f"Companies with metadata: {results.metadata.companies_with_metadata}")
        click.echo(f"Companies screened: {results.metadata.companies_screened}")
        click.echo(f"Excluded (no metadata): {results.metadata.excluded_no_metadata}")
        click.echo(f"Excluded (too young): {results.metadata.excluded_too_young}")

        if results.warnings:
            click.echo("\nWarnings:")
            for warning in results.warnings:
                click.echo(f"  - {warning}")

        if results.results:
            click.echo(f"\nTop 5 worst performers:")
            for i, result in enumerate(results.results[:5], 1):
                click.echo(
                    f"  {i}. {result.ticker} ({result.company_name}): "
                    f"{result.worst_5day_performance.return_pct:.2f}% "
                    f"({result.worst_5day_performance.start_date} to "
                    f"{result.worst_5day_performance.end_date})"
                )

        click.echo(f"\nResults saved to: {output}")
        click.echo("=" * 80)

    except Exception as e:
        logger.error(f"Screening failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--index",
    "-i",
    "indices",
    multiple=True,
    type=click.Choice(["SP500", "DAX", "FTSE100"], case_sensitive=False),
    help="Index to backtest (can specify multiple times). Default: all indices.",
)
@click.option(
    "--min-age",
    type=int,
    default=config.MIN_AGE_YEARS,
    help=f"Minimum company age in years (default: {config.MIN_AGE_YEARS})",
)
@click.option(
    "--country",
    "-c",
    "countries",
    multiple=True,
    help="Filter by country (can specify multiple times). Default: all countries.",
)
@click.option(
    "--metadata",
    type=click.Path(exists=True, path_type=Path),
    default=config.METADATA_CSV,
    help=f"Path to company metadata CSV (default: {config.METADATA_CSV})",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file path (default: output/backtest_results_<timestamp>.json)",
)
@click.option(
    "--lookback-years",
    type=int,
    default=5,
    help="Years to backtest (default: 5)",
)
@click.option(
    "--investment",
    type=float,
    default=50.0,
    help="Investment amount per trade in $ (default: 50)",
)
@click.option(
    "--frequency-days",
    type=int,
    default=7,
    help="Days between screening runs (default: 7 = weekly)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "--plot",
    "-p",
    is_flag=True,
    help="Generate plots (cumulative P&L and holding period distribution)",
)
def backtest(
    indices: tuple[str, ...],
    min_age: int,
    countries: tuple[str, ...],
    metadata: Path,
    output: Path | None,
    lookback_years: int,
    investment: float,
    frequency_days: int,
    verbose: bool,
    plot: bool,
):
    """
    Backtest mean reversion strategy over historical data.

    Strategy:
    - Screen weekly for worst 5-day performers (negative returns only)
    - Buy $50 (default) worth of stock at current price
    - Sell when stock recovers to 5-day-ago price (breakeven)

    Examples:

      # Backtest S&P 500 US companies for last 5 years
      uv run src/main.py backtest --index SP500 --country USA

      # Backtest with custom parameters
      uv run src/main.py backtest --index SP500 --country USA --lookback-years 3 --investment 100
    """
    from .backtesting.engine import BacktestEngine
    from .backtesting.reporter import print_backtest_summary, save_backtest_results
    from .backtesting.plotter import generate_backtest_plots

    # Set log level
    if verbose:
        logger.setLevel("DEBUG")

    # Default to all indices if none specified
    if not indices:
        indices = list(config.SUPPORTED_INDICES)
    else:
        indices = [idx.upper() for idx in indices]

    # Convert countries to list
    countries_list = list(countries) if countries else []

    # Generate default output path if not specified
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = config.OUTPUT_DIR / f"backtest_results_{timestamp}.json"

    try:
        # Create backtest engine
        engine = BacktestEngine(
            indices=indices,
            min_age_years=min_age,
            countries=countries_list,
            metadata_path=metadata,
            lookback_years=lookback_years,
            investment_per_trade=investment,
            screening_frequency_days=frequency_days,
        )

        # Run backtest
        result = engine.run()

        # Save results
        save_backtest_results(result, output)

        # Print summary
        print_backtest_summary(result)

        click.echo(f"\nDetailed results saved to: {output}")

        # Generate plots if requested
        if plot:
            click.echo("\nGenerating plots...")
            generate_backtest_plots(result, config.OUTPUT_DIR)
            click.echo("Plots saved!")

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
