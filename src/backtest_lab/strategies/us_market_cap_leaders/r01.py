from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from backtest_lab.core import Order, StrategyContext

STRATEGY_ID = "us_market_cap_leaders"
REVISION = "r01"

PRICE_START = "2010-03-31"
END_EXCLUSIVE = "2026-07-01"
REQUIRED_COLUMNS = ("AAPL", "AMZN", "GOOGL", "MSFT", "NVDA", "XOM", "SPY", "QQQ")
RANKING_FILE = Path(__file__).with_name("quarterly_rankings.csv")
RANKING_COLUMNS = (
    "ranking_date",
    "rank1_company",
    "rank1_ticker",
    "rank1_market_cap_b",
    "rank2_company",
    "rank2_ticker",
    "rank2_market_cap_b",
    "source_group",
    "confidence",
)


def load_rankings(path: str | Path = RANKING_FILE) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = [column for column in RANKING_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"ranking data missing required columns: {missing}")
    frame = frame.loc[:, RANKING_COLUMNS].copy()
    frame["ranking_date"] = pd.to_datetime(frame["ranking_date"])
    frame = frame.sort_values("ranking_date").reset_index(drop=True)
    if frame.empty:
        raise ValueError("ranking data must not be empty.")
    if frame["ranking_date"].duplicated().any():
        raise ValueError("ranking_date must be unique.")
    if not frame["ranking_date"].is_monotonic_increasing:
        raise ValueError("ranking_date must be increasing.")
    for column in ("rank1_market_cap_b", "rank2_market_cap_b"):
        frame[column] = frame[column].astype(float)
    if (frame["rank1_market_cap_b"] <= 0).any() or (frame["rank2_market_cap_b"] <= 0).any():
        raise ValueError("market caps must be positive.")
    if (frame["rank1_ticker"] == frame["rank2_ticker"]).any():
        raise ValueError("rank1_ticker and rank2_ticker must differ.")
    return frame


def required_symbols(rankings: pd.DataFrame) -> tuple[str, ...]:
    symbols = set(rankings["rank1_ticker"].astype(str)) | set(rankings["rank2_ticker"].astype(str))
    symbols.update({"SPY", "QQQ"})
    return tuple(sorted(symbols))


def find_active_start(prices: pd.DataFrame, rankings: pd.DataFrame | None = None) -> pd.Timestamp:
    rankings = load_rankings() if rankings is None else rankings
    first_ranking_date = pd.Timestamp(rankings.iloc[0]["ranking_date"])
    eligible = pd.DatetimeIndex(prices.index)[pd.DatetimeIndex(prices.index) > first_ranking_date]
    if eligible.empty:
        raise ValueError("price data has no timestamp after the first ranking date.")
    return pd.Timestamp(eligible[0])


def _target_weight_orders(
    context: StrategyContext,
    target_weights: Mapping[str, float],
    tolerance: float = 1e-9,
) -> list[Order]:
    total_value = context.portfolio.value(context.prices)
    symbols = sorted(set(context.portfolio.positions) | set(target_weights))
    orders: list[Order] = []
    for symbol in symbols:
        if symbol not in context.prices:
            raise KeyError(f"Missing current price for target symbol {symbol}.")
        target_quantity = (total_value * float(target_weights.get(symbol, 0.0))) / float(context.prices[symbol])
        difference = target_quantity - context.portfolio.quantity(symbol)
        if abs(difference) <= tolerance:
            continue
        orders.append(Order(symbol=symbol, side="buy" if difference > 0 else "sell", quantity=abs(difference)))
    return orders


@dataclass
class QuarterlyMarketCapLeaderStrategy:
    top_n: int
    rankings: pd.DataFrame = field(default_factory=load_rankings)
    decisions: list[dict[str, object]] = field(default_factory=list)
    _last_ranking_date: pd.Timestamp | None = None

    def __post_init__(self) -> None:
        if self.top_n not in {1, 2}:
            raise ValueError("top_n must be 1 or 2.")
        self.rankings = self.rankings.copy()
        self.rankings["ranking_date"] = pd.to_datetime(self.rankings["ranking_date"])
        self.rankings = self.rankings.sort_values("ranking_date").reset_index(drop=True)

    @property
    def name(self) -> str:
        return "TOP1" if self.top_n == 1 else "TOP2"

    def on_step(self, context: StrategyContext) -> list[Order]:
        timestamp = pd.Timestamp(context.timestamp)
        eligible = self.rankings.loc[self.rankings["ranking_date"] < timestamp]
        if eligible.empty:
            return []

        row = eligible.iloc[-1]
        ranking_date = pd.Timestamp(row["ranking_date"])
        if self._last_ranking_date == ranking_date:
            return []

        rank1 = str(row["rank1_ticker"])
        rank2 = str(row["rank2_ticker"])
        if self.top_n == 1:
            target = {rank1: 1.0}
        else:
            target = {rank1: 0.5, rank2: 0.5}

        self._last_ranking_date = ranking_date
        self.decisions.append(
            {
                "strategy": self.name,
                "ranking_date": ranking_date,
                "execution_date": timestamp,
                "rank1_company": row["rank1_company"],
                "rank1_ticker": rank1,
                "rank1_market_cap_b": float(row["rank1_market_cap_b"]),
                "rank2_company": row["rank2_company"],
                "rank2_ticker": rank2,
                "rank2_market_cap_b": float(row["rank2_market_cap_b"]),
                "rank1_weight": 1.0 if self.top_n == 1 else 0.5,
                "rank2_weight": 0.0 if self.top_n == 1 else 0.5,
                "source_group": row["source_group"],
                "confidence": row["confidence"],
            }
        )
        return _target_weight_orders(context, target)
