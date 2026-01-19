# SPDX-FileCopyrightText: 2025 Yannick Kees
#
# SPDX-License-Identifier: MIT
"""Backtesting engine for mean reversion strategy."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from ..data import company_metadata, index_fetcher, market_data
from ..filters import age_filter, country_filter, performance_filter
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Trade:
    """Represents a single trade."""

    ticker: str
    company_name: str
    entry_date: str
    entry_price: float
    shares: float
    target_price: float
    exit_date: str | None = None
    exit_price: float | None = None
    holding_days: int | None = None
    pnl: float | None = None


@dataclass
class BacktestResult:
    """Results from backtesting."""

    trades: list[Trade]
    total_pnl: float
    total_invested: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    still_open: int
    avg_holding_days: float
    holding_days_distribution: dict[str, int]  # Range -> count


class BacktestEngine:
    """Backtests the mean reversion strategy."""

    def __init__(
        self,
        indices: list[str],
        min_age_years: int,
        countries: list[str] | None = None,
        metadata_path: Path | None = None,
        lookback_years: int = 5,
        investment_per_trade: float = 50.0,
        screening_frequency_days: int = 7,
    ):
        """
        Initialize backtest engine.

        Args:
            indices: List of index names (e.g., ['SP500', 'DAX'])
            min_age_years: Minimum company age in years
            countries: List of countries to filter (None = all)
            metadata_path: Path to metadata CSV
            lookback_years: Years to backtest
            investment_per_trade: Amount to invest per trade ($)
            screening_frequency_days: Days between screening (default: 7 = weekly)
        """
        self.indices = indices
        self.min_age_years = min_age_years
        self.countries = countries or []
        self.metadata_path = metadata_path
        self.lookback_years = lookback_years
        self.investment_per_trade = investment_per_trade
        self.screening_frequency_days = screening_frequency_days

        # State
        self.open_positions: dict[str, Trade] = {}
        self.closed_trades: list[Trade] = []
        self.all_historical_data: dict[str, pd.DataFrame] = {}

    def run(self) -> BacktestResult:
        """
        Run the backtest simulation.

        Returns:
            BacktestResult with all trades and statistics
        """
        logger.info("=" * 80)
        logger.info("Starting backtest simulation")
        logger.info("=" * 80)
        logger.info(f"Indices: {', '.join(self.indices)}")
        logger.info(f"Countries: {self.countries or 'all'}")
        logger.info(f"Lookback period: {self.lookback_years} years")
        logger.info(f"Investment per trade: ${self.investment_per_trade}")
        logger.info(f"Screening frequency: every {self.screening_frequency_days} days")
        logger.info("=" * 80)

        # Step 1: Get all candidate tickers
        logger.info("\n[Step 1/4] Fetching candidate companies...")
        candidate_tickers = self._get_candidate_tickers()

        if not candidate_tickers:
            logger.error("No candidate tickers found!")
            return self._create_empty_result()

        # Step 2: Fetch all historical data
        logger.info("\n[Step 2/4] Fetching historical data for all candidates...")
        self._fetch_all_historical_data(candidate_tickers)

        if not self.all_historical_data:
            logger.error("No historical data fetched!")
            return self._create_empty_result()

        # Step 3: Simulate weekly screenings
        logger.info("\n[Step 3/4] Simulating weekly screenings...")
        self._simulate_screenings()

        # Step 4: Close any remaining open positions at today's price
        logger.info("\n[Step 4/4] Closing remaining open positions...")
        self._close_remaining_positions()

        # Generate results
        result = self._generate_results()

        logger.info("=" * 80)
        logger.info("Backtest complete!")
        logger.info("=" * 80)

        return result

    def _get_candidate_tickers(self) -> list[str]:
        """Get all candidate tickers that pass initial filters."""
        # Fetch index constituents
        all_tickers = []
        for index_name in self.indices:
            try:
                tickers = index_fetcher.fetch_index_tickers(index_name)
                all_tickers.extend(tickers)
                logger.info(f"  {index_name}: {len(tickers)} tickers")
            except Exception as e:
                logger.error(f"  Failed to fetch {index_name}: {e}")

        logger.info(f"\nTotal tickers from indices: {len(all_tickers)}")

        # Load metadata
        metadata_df = company_metadata.load_metadata(self.metadata_path)
        logger.info(f"Loaded metadata for {len(metadata_df)} companies")

        # Filter by metadata
        filtered_df = company_metadata.get_companies_by_tickers(metadata_df, all_tickers)
        logger.info(f"Companies with metadata: {len(filtered_df)}")

        # Apply age filter
        filtered_df = age_filter.filter_by_age(filtered_df, self.min_age_years)

        # Apply country filter
        if self.countries:
            filtered_df = country_filter.filter_by_country(filtered_df, self.countries)

        logger.info(f"Companies after filters: {len(filtered_df)}")

        return filtered_df["ticker"].tolist()

    def _fetch_all_historical_data(self, tickers: list[str]) -> None:
        """Fetch historical data for all tickers."""
        # Fetch data for lookback period + buffer
        lookback_days = self.lookback_years * 365 + 30  # Extra buffer

        self.all_historical_data = market_data.fetch_multiple_stocks(
            tickers, lookback_days=lookback_days
        )

        logger.info(
            f"Successfully fetched data for {len(self.all_historical_data)}/{len(tickers)} tickers"
        )

    def _simulate_screenings(self) -> None:
        """Simulate weekly screenings over the backtest period."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_years * 365)

        current_date = start_date
        screening_count = 0

        while current_date <= end_date:
            screening_count += 1
            logger.info(f"\nScreening #{screening_count}: {current_date.date()}")

            # Update open positions (check for exits)
            self._update_open_positions(current_date)

            # Run screening for this date
            worst_stock = self._screen_for_date(current_date)

            # Open new position if found
            if worst_stock:
                self._open_position(worst_stock, current_date)

            # Move to next screening date
            current_date += timedelta(days=self.screening_frequency_days)

        logger.info(f"\nCompleted {screening_count} screenings")

    def _screen_for_date(self, screening_date: datetime) -> dict | None:
        """
        Screen for worst performer on a specific date.

        Returns:
            Dictionary with ticker, entry_price, target_price, company_name
            or None if no valid stocks found
        """
        candidates = []

        for ticker, hist in self.all_historical_data.items():
            # Get data up to screening date
            # Handle timezone-aware datetime comparison
            if hist.index.tz is not None:
                # Convert screening_date to timezone-aware
                screening_date_tz = pd.Timestamp(screening_date).tz_localize(hist.index.tz)
                hist_up_to_date = hist[hist.index <= screening_date_tz]
            else:
                hist_up_to_date = hist[hist.index <= screening_date]

            # Only look at the last 5-7 trading days (not entire history!)
            if len(hist_up_to_date) < 10:  # Need at least 10 days
                continue

            # Take only the last 10 days for performance calculation
            # This ensures we find the RECENT worst 5-day window
            hist_recent = hist_up_to_date.tail(10)

            # Calculate worst 5-day performance in recent window
            perf = performance_filter.calculate_worst_5day_performance(hist_recent)

            if perf is None or perf.return_pct >= 0:
                continue  # Only consider negative returns

            # Get current price at screening date
            current_price = market_data.get_price_on_date(hist, screening_date)

            if current_price is None:
                continue

            candidates.append(
                {
                    "ticker": ticker,
                    "return_pct": perf.return_pct,
                    "entry_price": float(current_price),
                    "target_price": perf.start_price,
                    "company_name": ticker,  # Will be updated later if needed
                }
            )

        if not candidates:
            logger.debug("  No candidates with negative returns found")
            return None

        # Sort by worst performance
        candidates.sort(key=lambda x: x["return_pct"])

        worst = candidates[0]
        logger.info(
            f"  Found: {worst['ticker']} (return: {worst['return_pct']:.2f}%, "
            f"entry: ${worst['entry_price']:.2f}, target: ${worst['target_price']:.2f})"
        )

        return worst

    def _open_position(self, stock_info: dict, entry_date: datetime) -> None:
        """Open a new trading position."""
        ticker = stock_info["ticker"]

        # Skip if already have open position
        if ticker in self.open_positions:
            logger.debug(f"  Already have open position in {ticker}, skipping")
            return

        # Safety check: target price must be higher than entry price
        if stock_info["target_price"] <= stock_info["entry_price"]:
            logger.warning(
                f"  SKIPPED {ticker}: target_price ({stock_info['target_price']:.2f}) "
                f"<= entry_price ({stock_info['entry_price']:.2f})"
            )
            return

        shares = self.investment_per_trade / stock_info["entry_price"]

        trade = Trade(
            ticker=ticker,
            company_name=stock_info["company_name"],
            entry_date=entry_date.strftime("%Y-%m-%d"),
            entry_price=stock_info["entry_price"],
            shares=shares,
            target_price=stock_info["target_price"],
        )

        self.open_positions[ticker] = trade
        logger.info(
            f"  OPENED: {ticker} - {shares:.4f} shares @ ${stock_info['entry_price']:.2f} "
            f"(target: ${stock_info['target_price']:.2f})"
        )

    def _update_open_positions(self, current_date: datetime) -> None:
        """Check if any open positions should be closed."""
        positions_to_close = []

        for ticker, trade in self.open_positions.items():
            # Get current price
            if ticker not in self.all_historical_data:
                continue

            current_price = market_data.get_price_on_date(
                self.all_historical_data[ticker], current_date
            )

            if current_price is None:
                continue

            # Check if target reached
            if current_price >= trade.target_price:
                positions_to_close.append((ticker, current_price, current_date))

        # Close positions
        for ticker, exit_price, exit_date in positions_to_close:
            self._close_position(ticker, exit_price, exit_date)

    def _close_position(
        self, ticker: str, exit_price: float, exit_date: datetime
    ) -> None:
        """Close a trading position."""
        if ticker not in self.open_positions:
            return

        trade = self.open_positions[ticker]

        # Calculate holding period
        entry_dt = datetime.strptime(trade.entry_date, "%Y-%m-%d")
        holding_days = (exit_date - entry_dt).days

        # Calculate P&L
        pnl = trade.shares * (exit_price - trade.entry_price)

        # Update trade
        trade.exit_date = exit_date.strftime("%Y-%m-%d")
        trade.exit_price = exit_price
        trade.holding_days = holding_days
        trade.pnl = pnl

        logger.info(
            f"  CLOSED: {ticker} - held {holding_days} days, "
            f"P&L: ${pnl:.2f} ({(pnl / self.investment_per_trade * 100):.1f}%)"
        )

        # Move to closed trades
        self.closed_trades.append(trade)
        del self.open_positions[ticker]

    def _close_remaining_positions(self) -> None:
        """Close all remaining open positions at current price."""
        current_date = datetime.now()

        for ticker in list(self.open_positions.keys()):
            if ticker not in self.all_historical_data:
                continue

            current_price = market_data.get_price_on_date(
                self.all_historical_data[ticker], current_date
            )

            if current_price is not None:
                self._close_position(ticker, float(current_price), current_date)
            else:
                logger.warning(f"Could not close position in {ticker} - no current price")

    def _generate_results(self) -> BacktestResult:
        """Generate backtest results."""
        all_trades = self.closed_trades + list(self.open_positions.values())

        # Calculate statistics
        total_pnl = sum(t.pnl for t in self.closed_trades if t.pnl is not None)
        total_invested = len(all_trades) * self.investment_per_trade
        total_trades = len(all_trades)
        winning_trades = sum(1 for t in self.closed_trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in self.closed_trades if t.pnl and t.pnl < 0)
        still_open = len(self.open_positions)

        # Calculate holding days statistics
        closed_holding_days = [t.holding_days for t in self.closed_trades if t.holding_days]
        avg_holding_days = (
            sum(closed_holding_days) / len(closed_holding_days)
            if closed_holding_days
            else 0
        )

        # Create holding days distribution
        distribution = self._create_holding_distribution(closed_holding_days)

        logger.info(f"\nTotal trades: {total_trades}")
        logger.info(f"Closed trades: {len(self.closed_trades)}")
        logger.info(f"Still open: {still_open}")
        logger.info(f"Winning trades: {winning_trades}")
        logger.info(f"Losing trades: {losing_trades}")
        logger.info(f"Total P&L: ${total_pnl:.2f}")
        logger.info(f"Total invested: ${total_invested:.2f}")
        logger.info(
            f"Return: {(total_pnl / total_invested * 100):.2f}%"
            if total_invested > 0
            else "N/A"
        )
        logger.info(f"Average holding days: {avg_holding_days:.1f}")

        return BacktestResult(
            trades=all_trades,
            total_pnl=total_pnl,
            total_invested=total_invested,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            still_open=still_open,
            avg_holding_days=avg_holding_days,
            holding_days_distribution=distribution,
        )

    def _create_holding_distribution(self, holding_days: list[int]) -> dict[str, int]:
        """Create distribution of holding periods."""
        if not holding_days:
            return {}

        distribution = defaultdict(int)
        ranges = [
            (0, 7, "0-7 days"),
            (7, 14, "7-14 days"),
            (14, 30, "14-30 days"),
            (30, 60, "30-60 days"),
            (60, 90, "60-90 days"),
            (90, 180, "90-180 days"),
            (180, 365, "180-365 days"),
            (365, float("inf"), "365+ days"),
        ]

        for days in holding_days:
            for min_days, max_days, label in ranges:
                if min_days <= days < max_days:
                    distribution[label] += 1
                    break

        return dict(distribution)

    def _create_empty_result(self) -> BacktestResult:
        """Create empty result when no data available."""
        return BacktestResult(
            trades=[],
            total_pnl=0.0,
            total_invested=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            still_open=0,
            avg_holding_days=0.0,
            holding_days_distribution={},
        )
