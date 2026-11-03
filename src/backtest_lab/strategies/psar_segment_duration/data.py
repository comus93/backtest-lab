from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from backtest_lab.data import DataCoverageError


def load_fdr_prices(start: str | date, end: str | date) -> pd.DataFrame:
    """Load QQQ OHLCV plus QQQ/QLD/PSQ close prices from FinanceDataReader.

    Rows are restricted to the complete-date intersection. No fill or price
    substitution is performed. Close is intentionally the common execution
    series; raw OHLC is retained for auditability of the PSAR signal.
    """
    import FinanceDataReader as fdr

    frames: dict[str, pd.DataFrame] = {}
    for ticker in ("QQQ", "QLD", "PSQ"):
        frame = fdr.DataReader(ticker, start, end)
        if frame.empty:
            raise DataCoverageError(f"FDR returned no rows for {ticker}.")
        frame = frame.copy()
        frame.index = pd.to_datetime(frame.index)
        required = {"Open", "High", "Low", "Close"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise DataCoverageError(f"FDR {ticker} data missing columns: {missing}")
        if frame.index.has_duplicates:
            raise DataCoverageError(f"FDR {ticker} data has duplicate dates.")
        frames[ticker] = frame.sort_index()

    common = frames["QQQ"].index.intersection(frames["QLD"].index).intersection(frames["PSQ"].index)
    if common.empty:
        raise DataCoverageError("FDR symbols have no common trading dates.")
    # A missing QLD/PSQ trading day would silently compress PSAR duration,
    # potentially turning a 5-day trend into a 4-day trend. Reject gaps.
    qqq_trade_dates = frames["QQQ"].index
    expected = qqq_trade_dates[(qqq_trade_dates >= common.min()) & (qqq_trade_dates <= common.max())]
    if not expected.equals(common.sort_values()):
        missing = expected.difference(common)
        raise DataCoverageError(f"ETF trading dates missing relative to QQQ: {missing[:5].tolist()}")
    output = pd.DataFrame(index=common.sort_values())
    for column in ("Open", "High", "Low", "Close"):
        output[f"QQQ_{column}"] = frames["QQQ"].loc[common, column].astype(float)
    if "Volume" in frames["QQQ"]:
        output["QQQ_Volume"] = frames["QQQ"].loc[common, "Volume"].astype(float)
        volume = output["QQQ_Volume"]
        if volume.isna().any() or (~np.isfinite(volume)).any() or (volume < 0).any():
            raise DataCoverageError("FDR QQQ Volume contains invalid observations")
    output["QQQ"] = output["QQQ_Close"]
    output["QLD"] = frames["QLD"].loc[common, "Close"].astype(float)
    output["PSQ"] = frames["PSQ"].loc[common, "Close"].astype(float)
    if output.isna().any().any():
        raise DataCoverageError("FDR common price frame contains missing values; no fill was applied.")
    if (output[["QQQ_High", "QQQ_Low", "QQQ", "QLD", "PSQ"]] <= 0).any().any():
        raise DataCoverageError("FDR common price frame contains non-positive prices.")
    if (output["QQQ_High"] < output[["QQQ_Open", "QQQ_Close"]].max(axis=1)).any():
        raise DataCoverageError("FDR QQQ High is below its Open/Close.")
    if (output["QQQ_Low"] > output[["QQQ_Open", "QQQ_Close"]].min(axis=1)).any():
        raise DataCoverageError("FDR QQQ Low is above its Open/Close.")
    # Close series must be split-adjusted consistently, especially PSQ's
    # reverse splits. A large, isolated tracking discrepancy invalidates NAV.
    returns = output[["QQQ", "QLD", "PSQ"]].pct_change().dropna()
    if ((returns["QLD"] - 2 * returns["QQQ"]).abs() > 0.35).any():
        raise DataCoverageError("QLD close discontinuity: verify split adjustment and data source.")
    if ((returns["PSQ"] + returns["QQQ"]).abs() > 0.35).any():
        raise DataCoverageError("PSQ close discontinuity: verify reverse-split adjustment.")
    return output
