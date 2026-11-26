"""Explicit external signal / Korea ETF instrument mapping for the SMA study.

Do not infer ticker replacements. Proxy exceptions are disclosed in this registry.
FDR domestic Close is a PRICE series, not a guaranteed total-return index.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd

from .r01 import AssetInput, END, START


@dataclass(frozen=True)
class AssetMapping:
    asset_id: str
    display_name: str
    reference_ticker: str
    reference_source: str  # yahoo, fdr, domestic
    long_etf: str
    inverse_etf: str | None = None
    proxy_note: str = ""


ASSETS: tuple[AssetMapping, ...] = (
    AssetMapping("sp500", "미국 S&P500", "SPY", "yahoo", "219480", "225030",
                 "US equity index ETF vs KR futures-hedged ETF; not identical return series"),
    AssetMapping("nasdaq100", "미국 나스닥100", "QQQ", "yahoo", "304940", "409810",
                 "US equity ETF vs KR futures-hedged ETF"),
    AssetMapping("russell2000", "미국 러셀2000", "IWM", "yahoo", "280930"),
    AssetMapping("kospi200", "한국 코스피200", "KS200", "fdr", "069500", "114800"),
    AssetMapping("msci_korea", "한국 MSCI", "EWY", "yahoo", "310970", None,
                 "EWY benchmark variant differs from TIGER MSCI Korea TR; proxy only"),
    AssetMapping("nikkei225", "일본 니케이225", "^N225", "yahoo", "241180"),
    AssetMapping("topix", "일본 TOPIX", "1306.T", "yahoo", "195920", "205720",
                 "1306.T is a Japanese TOPIX ETF proxy, not the index itself"),
    AssetMapping("csi300", "중국 CSI300", "ASHR", "yahoo", "283580", "217780",
                 "ASHR is a US-listed CSI300 ETF proxy, not the raw index"),
    AssetMapping("nifty50", "인도 Nifty50", "^NSEI", "yahoo", "453810"),
    AssetMapping("emerging", "신흥국 MSCI", "EEM", "yahoo", "195980", None,
                 "Check MSCI benchmark and currency hedge variant"),
    AssetMapping("eurostoxx50", "유럽 Euro STOXX 50", "FEZ", "yahoo", "195930", None,
                 "FEZ is a US-listed ETF proxy; domestic product is KRW hedged"),
    AssetMapping("gold", "금", "GLD", "yahoo", "132030", "280940",
                 "GLD holds physical gold; Korea-listed ETF uses gold futures, with roll costs"),
    AssetMapping("silver", "은", "SLV", "yahoo", "144600", None,
                 "SLV physical silver vs KR silver futures ETF"),
    AssetMapping("copper", "구리", "CPER", "yahoo", "138910", None,
                 "Copper futures fund methodologies may differ"),
    AssetMapping("wti", "WTI 원유", "USO", "yahoo", "261220", "271050",
                 "Both are futures funds; their roll methodologies can differ"),
    AssetMapping("grains", "3대 농산물", "271060", "domestic", "271060", None,
                 "No verified overseas matching index feed; interim domestic ETF signal"),
    AssetMapping("soybeans", "대두", "SOYB", "yahoo", "138920", None,
                 "SOYB vs Korea futures roll methodologies may differ"),
    AssetMapping("agriculture", "농산물 종합", "DBA", "yahoo", "137610", None,
                 "DBA broad agriculture basket is only an approximate benchmark"),
)
assert len(ASSETS) == len({x.asset_id for x in ASSETS}) == 18


def _fdr_history(ticker: str, start: str, end: str) -> pd.Series:
    import FinanceDataReader as fdr

    frame = fdr.DataReader(ticker, start, end)
    if "Close" not in frame or frame.empty:
        raise ValueError(f"FDR {ticker}: unavailable Close")
    close = frame["Close"].copy()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.astype(float)


def _yahoo_history(ticker: str, start: str, end: str) -> pd.Series:
    import yfinance as yf

    frame = yf.download(ticker, start=start, end=end, auto_adjust=False,
                        progress=False, threads=False)
    if frame.empty:
        raise ValueError(f"Yahoo {ticker}: unavailable data")
    # Adjusted prices (where published) are the reference series; the local
    # executable ETF uses actual FDR trading Close, not synthetic inverse.
    column = "Adj Close" if "Adj Close" in frame else "Close"
    close = frame[column]
    if isinstance(close, pd.DataFrame):
        if close.shape[1] != 1:
            raise ValueError(f"Yahoo {ticker}: non-unique price column")
        close = close.iloc[:, 0]
    close = close.copy()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.astype(float)


def load_price_snapshot(
    start: str = "2016-01-01",
    end: str = END,
    yahoo_reader: Callable[[str, str, str], pd.Series] = _yahoo_history,
    fdr_reader: Callable[[str, str, str], pd.Series] = _fdr_history,
) -> pd.DataFrame:
    """Load each approved instrument explicitly; missing data fail loudly.

    The returned frame has a union of trading dates with NaNs for market
    holidays, NOT a cross-market forward-filled or intersected date index.
    This exact snapshot is preserved as input_prices.csv by GitHub Actions.
    """
    if not start < end:
        raise ValueError("start must be strictly before end")
    series = {}
    cache: dict[tuple[str, str], pd.Series] = {}

    def read(source: str, ticker: str) -> pd.Series:
        key = (source, ticker)
        if key not in cache:
            loader = yahoo_reader if source == "yahoo" else fdr_reader
            cache[key] = loader(ticker, start, end)
        return cache[key]

    for item in ASSETS:
        ref_source = "fdr" if item.reference_source == "domestic" else item.reference_source
        series[f"{item.asset_id}__reference"] = read(ref_source, item.reference_ticker)
        series[f"{item.asset_id}__long"] = read("fdr", item.long_etf)
        if item.inverse_etf:
            series[f"{item.asset_id}__inverse"] = read("fdr", item.inverse_etf)
    prices = pd.concat(series, axis=1).sort_index()
    prices.index.name = "timestamp"
    if prices.index.has_duplicates or prices.empty:
        raise ValueError("Malformed price snapshot")
    return prices


def extract_assets(prices: pd.DataFrame) -> list[AssetInput]:
    items = []
    for row in ASSETS:
        required = [f"{row.asset_id}__reference", f"{row.asset_id}__long"]
        if row.inverse_etf:
            required.append(f"{row.asset_id}__inverse")
        missing = sorted(set(required) - set(prices.columns))
        if missing:
            raise ValueError(f"{row.asset_id}: missing snapshot columns {missing}")
        items.append(AssetInput(
            asset_id=row.asset_id, display_name=row.display_name,
            reference_close=prices[f"{row.asset_id}__reference"].dropna(),
            long_close=prices[f"{row.asset_id}__long"].dropna(),
            long_symbol=row.long_etf,
            inverse_close=prices[f"{row.asset_id}__inverse"].dropna()
            if row.inverse_etf else None,
            inverse_symbol=row.inverse_etf,
        ))
    return items
