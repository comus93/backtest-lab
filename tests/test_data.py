import pandas as pd
import pytest

from backtest_lab.data import (
    DataCoverageError,
    FinanceDataReaderMarketDataLoader,
    MarketDataConfig,
    MySqlConfig,
    YahooFinanceMarketDataLoader,
    load_market_data,
)


def test_finance_datareader_loader_normalizes_stubbed_prices() -> None:
    def reader(ticker, start, end):
        assert (start, end) == ("2024-01-01", "2024-01-02")
        return pd.DataFrame(
            {"Close": [100.0 if ticker == "AAA" else 200.0]},
            index=pd.to_datetime(["2024-01-01"]),
        )

    prices = FinanceDataReaderMarketDataLoader(reader).load_prices(
        ["AAA", "BBB"], "2024-01-01", "2024-01-02"
    )

    assert list(prices.columns) == ["AAA", "BBB"]
    assert prices.loc[pd.Timestamp("2024-01-01"), "AAA"] == pytest.approx(100.0)
    assert prices.loc[pd.Timestamp("2024-01-01"), "BBB"] == pytest.approx(200.0)


def test_yahoo_loader_uses_adjusted_close_from_stub() -> None:
    def history(ticker, start, end):
        return pd.DataFrame(
            {"Adj Close": [123.0]},
            index=pd.to_datetime(["2024-01-01"]),
        )

    prices = YahooFinanceMarketDataLoader(history).load_prices(["SPY"], "2024-01-01", "2024-01-02")

    assert prices.iloc[0, 0] == pytest.approx(123.0)


def test_yahoo_loader_normalizes_single_ticker_multiindex_response() -> None:
    columns = pd.MultiIndex.from_tuples([("Adj Close", "SPY")])
    frame = pd.DataFrame([[123.0]], columns=columns, index=pd.to_datetime(["2024-01-01"]))

    prices = YahooFinanceMarketDataLoader(lambda ticker, start, end: frame).load_prices(
        ["SPY"], "2024-01-01", "2024-01-02"
    )

    assert prices.loc[pd.Timestamp("2024-01-01"), "SPY"] == pytest.approx(123.0)


def test_on_demand_loader_rejects_missing_price_column() -> None:
    loader = YahooFinanceMarketDataLoader(
        lambda ticker, start, end: pd.DataFrame({"Close": [1.0]}, index=pd.to_datetime(["2024-01-01"]))
    )

    with pytest.raises(DataCoverageError, match="missing price column"):
        loader.load_prices(["SPY"], "2024-01-01", "2024-01-02")


def test_market_data_input_applies_explicit_symbol_mapping(monkeypatch) -> None:
    class StubMySqlLoader:
        def __init__(self, config):
            pass

        def load_prices(self, tickers, start, end, price_column, require_full_coverage):
            return pd.DataFrame({tickers[0]: [70000.0]}, index=pd.to_datetime(["2024-01-01"]))

    monkeypatch.setattr("backtest_lab.data.MySqlMarketDataLoader", StubMySqlLoader)
    prices = load_market_data(
        ["KOREAN_STOCK"],
        "2024-01-01",
        "2024-01-02",
        config=MarketDataConfig(symbol_mapping={"KOREAN_STOCK": "005930"}),
        mysql_config=MySqlConfig("host", "user", "password", "database"),
    )

    assert list(prices.columns) == ["KOREAN_STOCK"]
    assert prices.iloc[0, 0] == pytest.approx(70000.0)
