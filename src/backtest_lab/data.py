from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Callable, Iterable, Mapping

import pandas as pd
import pymysql
from dotenv import dotenv_values


class DataCoverageError(Exception):
    pass


class DataSource(str, Enum):
    LOCAL_MYSQL = "local_mysql"
    FINANCE_DATA_READER = "finance_datareader"
    YAHOO_FINANCE = "yahoo_finance"


@dataclass(frozen=True)
class MarketDataConfig:
    source: DataSource = DataSource.LOCAL_MYSQL
    symbol_mapping: Mapping[str, str] = field(default_factory=dict)
    price_column: str = "AdjClose"
    require_full_coverage: bool = True

    def source_ticker(self, symbol: str) -> str:
        return str(self.symbol_mapping.get(symbol, symbol))


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


class FinanceDataReaderMarketDataLoader:
    def __init__(self, data_reader: Callable[[str, str | date, str | date], pd.DataFrame] | None = None) -> None:
        self._data_reader = data_reader

    def load_prices(
        self,
        tickers: Iterable[str],
        start: str | date,
        end: str | date,
        price_column: str = "AdjClose",
    ) -> pd.DataFrame:
        reader = self._data_reader or self._default_data_reader
        return _load_on_demand_prices(reader, tickers, start, end, price_column, {"AdjClose": "Close"})

    @staticmethod
    def _default_data_reader(ticker: str, start: str | date, end: str | date) -> pd.DataFrame:
        import FinanceDataReader as fdr

        return fdr.DataReader(ticker, start, end)


class YahooFinanceMarketDataLoader:
    def __init__(self, history_loader: Callable[[str, str | date, str | date], pd.DataFrame] | None = None) -> None:
        self._history_loader = history_loader

    def load_prices(
        self,
        tickers: Iterable[str],
        start: str | date,
        end: str | date,
        price_column: str = "AdjClose",
    ) -> pd.DataFrame:
        loader = self._history_loader or self._default_history_loader
        return _load_on_demand_prices(loader, tickers, start, end, price_column, {"AdjClose": "Adj Close"})

    @staticmethod
    def _default_history_loader(ticker: str, start: str | date, end: str | date) -> pd.DataFrame:
        import yfinance as yf

        return yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)


def load_market_data(
    symbols: Iterable[str],
    start: str | date,
    end: str | date,
    config: MarketDataConfig | None = None,
    mysql_config: MySqlConfig | None = None,
) -> pd.DataFrame:
    config = config or MarketDataConfig()
    symbols = [str(symbol) for symbol in symbols]
    if not symbols:
        raise ValueError("symbols must not be empty.")
    source_tickers = [config.source_ticker(symbol) for symbol in symbols]
    if len(set(source_tickers)) != len(source_tickers):
        raise ValueError("symbol_mapping must map each requested symbol to a distinct source ticker.")

    if config.source is DataSource.LOCAL_MYSQL:
        if mysql_config is None:
            raise ValueError("mysql_config is required for the local_mysql data source.")
        prices = MySqlMarketDataLoader(mysql_config).load_prices(
            source_tickers,
            start,
            end,
            price_column=config.price_column,
            require_full_coverage=config.require_full_coverage,
        )
    elif config.source is DataSource.FINANCE_DATA_READER:
        prices = FinanceDataReaderMarketDataLoader().load_prices(
            source_tickers, start, end, price_column=config.price_column
        )
    elif config.source is DataSource.YAHOO_FINANCE:
        prices = YahooFinanceMarketDataLoader().load_prices(
            source_tickers, start, end, price_column=config.price_column
        )
    else:
        raise ValueError(f"Unsupported data source: {config.source}")

    normalized = prices.loc[:, source_tickers].copy()
    normalized.columns = symbols
    return normalized


def _load_on_demand_prices(
    loader: Callable[[str, str | date, str | date], pd.DataFrame],
    tickers: Iterable[str],
    start: str | date,
    end: str | date,
    price_column: str,
    column_aliases: Mapping[str, str],
) -> pd.DataFrame:
    tickers = [str(ticker) for ticker in tickers]
    if not tickers:
        raise ValueError("tickers must not be empty.")
    source_column = column_aliases.get(price_column, price_column)
    series: list[pd.Series] = []
    for ticker in tickers:
        frame = loader(ticker, start, end)
        if source_column not in frame.columns:
            raise DataCoverageError(f"{ticker}: missing price column {source_column}")
        value = frame[source_column].rename(ticker)
        value.index = pd.to_datetime(value.index)
        series.append(value)
    prices = pd.concat(series, axis=1).sort_index().dropna()
    if prices.empty:
        raise DataCoverageError("No complete price rows found for requested tickers and period.")
    if prices.index.has_duplicates:
        raise DataCoverageError("Price index must not contain duplicates.")
    return prices.astype(float)
