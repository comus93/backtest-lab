from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd
import pymysql
from dotenv import dotenv_values


class DataCoverageError(Exception):
    pass


@dataclass(frozen=True)
class MySqlConfig:
    host: str
    user: str
    password: str
    database: str
    port: int = 3306

    @classmethod
    def from_env(cls, path: str = ".env") -> "MySqlConfig":
        values = dotenv_values(path)
        missing = [key for key in ["DB_HOST", "DB_USER", "DB_PASS", "DB_NAME"] if not values.get(key)]
        if missing:
            raise ValueError(f"Missing DB settings: {missing}")
        return cls(
            host=str(values["DB_HOST"]),
            user=str(values["DB_USER"]),
            password=str(values["DB_PASS"]),
            database=str(values["DB_NAME"]),
            port=int(values.get("DB_PORT") or 3306),
        )


class MySqlMarketDataLoader:
    def __init__(self, config: MySqlConfig) -> None:
        self.config = config

    def load_prices(
        self,
        tickers: Iterable[str],
        start: str | date,
        end: str | date,
        price_column: str = "AdjClose",
        require_full_coverage: bool = True,
    ) -> pd.DataFrame:
        tickers = [str(ticker) for ticker in tickers]
        if not tickers:
            raise ValueError("tickers must not be empty.")
        if price_column not in {"Open", "High", "Low", "Close", "AdjClose"}:
            raise ValueError(f"Unsupported price column: {price_column}")

        conn = pymysql.connect(
            host=self.config.host,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            port=self.config.port,
            charset="utf8mb4",
        )
        try:
            if require_full_coverage:
                self._validate_coverage(conn, tickers, start, end)
            placeholders = ", ".join(["%s"] * len(tickers))
            sql = (
                f"select Date, ticker, `{price_column}` as price "
                f"from global_price "
                f"where ticker in ({placeholders}) and Date between %s and %s "
                f"order by Date, ticker"
            )
            with conn.cursor() as cur:
                cur.execute(sql, [*tickers, start, end])
                frame = pd.DataFrame(cur.fetchall(), columns=["Date", "ticker", "price"])
        finally:
            conn.close()

        if frame.empty:
            raise DataCoverageError("No price rows found for requested tickers and period.")
        prices = frame.pivot(index="Date", columns="ticker", values="price").sort_index()
        prices.index = pd.to_datetime(prices.index)
        prices = prices.dropna()
        missing = [ticker for ticker in tickers if ticker not in prices.columns]
        if missing:
            raise DataCoverageError(f"No complete price data for tickers: {missing}")
        return prices[tickers].astype(float)

    @staticmethod
    def _validate_coverage(conn, tickers: list[str], start: str | date, end: str | date) -> None:
        placeholders = ", ".join(["%s"] * len(tickers))
        sql = (
            f"select ticker, min(Date), max(Date), count(*) "
            f"from global_price where ticker in ({placeholders}) group by ticker"
        )
        with conn.cursor() as cur:
            cur.execute(sql, tickers)
            rows = cur.fetchall()
        coverage = {str(row[0]): row for row in rows}
        errors: list[str] = []
        start_ts = pd.Timestamp(start).date()
        end_ts = pd.Timestamp(end).date()
        for ticker in tickers:
            row = coverage.get(ticker)
            if row is None:
                errors.append(f"{ticker}: no rows")
                continue
            min_date = pd.Timestamp(row[1]).date()
            max_date = pd.Timestamp(row[2]).date()
            if min_date > start_ts or max_date < end_ts:
                errors.append(f"{ticker}: available {min_date} to {max_date}, requested {start_ts} to {end_ts}")
        if errors:
            raise DataCoverageError("; ".join(errors))
