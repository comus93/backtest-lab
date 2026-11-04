"""PSAR QLD/Cash adapter: legacy CSV schema -> strategy-independent ReportData."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..models import (OverlayConfig, ReportConfig, ReportData, ReportPeriod,
                      SeriesConfig)
from ..tables import performance_matrix


WINDOWS = ("2007-2011", "2012-2016", "2017-2021", "2022-2026")
PALETTE = {"strategy": "#2563eb", "QLD": "#f97316", "QQQ": "#71717a"}
PSAR_UP_COLOR = "#8C786A"  # desaturated brown
PSAR_DOWN_COLOR = "#8B7F99"  # desaturated purple


def load_outputs(run_dir: str | Path, volume_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Read existing run results as immutable inputs, never regenerate statistics."""
    path = Path(run_dir)
    names = ("input_prices", "daily_signals", "equity_curves", "fills",
             "performance_summary", "ffn_stats")
    if not all((path / f"{name}.csv").is_file() for name in names):
        raise FileNotFoundError(f"Missing required report input in {path}")
    data = {name: pd.read_csv(path / f"{name}.csv") for name in names}
    for name in ("input_prices", "equity_curves"):
        data[name]["timestamp"] = pd.to_datetime(data[name]["timestamp"])
        if data[name]["timestamp"].duplicated().any():
            raise ValueError(f"Duplicate timestamps in {name}")
        data[name] = data[name].set_index("timestamp").sort_index()
    for name, column in (("daily_signals", "signal_date"), ("fills", "timestamp")):
        data[name][column] = pd.to_datetime(data[name][column])
    supplement = Path(volume_path) if volume_path else path / "qqq_volume.csv"
    if supplement.is_file():
        if "QQQ_Volume" in data["input_prices"]:
            raise ValueError("QQQ_Volume is present in both source prices and supplement")
        volume = pd.read_csv(supplement, parse_dates=["timestamp"])
        if set(volume.columns) != {"timestamp", "QQQ_Volume"}:
            raise ValueError("Invalid QQQ volume columns")
        if volume["timestamp"].duplicated().any():
            raise ValueError("Duplicate QQQ volume timestamps")
        volume = volume.set_index("timestamp")["QQQ_Volume"]
        data["input_prices"]["QQQ_Volume"] = volume.reindex(data["input_prices"].index)
    if "QQQ_Volume" in data["input_prices"]:
        values = data["input_prices"]["QQQ_Volume"]
        if values.isna().any() or (~np.isfinite(values)).any() or (values < 0).any():
            raise ValueError("QQQ Volume must have complete non-negative finite observations")
    return data


def window_data(data: dict[str, pd.DataFrame], window: str) -> dict[str, object]:
    """Validate and isolate one independent backtest window."""
    if window not in WINDOWS:
        raise ValueError(f"Unsupported window: {window}")
    selected = data["performance_summary"].query("window == @window")
    if len(selected) != 3:
        raise ValueError(f"Expected strategy + 2 benchmarks for {window}")
    strategy_rows = selected[selected["strategy"].str.startswith("PSAR Long Only ")]
    if len(strategy_rows) != 1:
        raise ValueError(f"Expected PSAR Long Only results for {window}")
    strategy = strategy_rows.iloc[0]["strategy"]
    names = {"strategy": strategy,
             "QLD": f"QLD Buy & Hold {window}",
             "QQQ": f"QQQ Buy & Hold {window}"}
    times = data["daily_signals"].query("window == @window").copy().sort_values("signal_date")
    if times.empty or times["signal_date"].duplicated().any():
        raise ValueError(f"Bad or absent daily signals for {window}")
    start, end = times["signal_date"].min(), times["signal_date"].max()
    price = data["input_prices"].loc[start:end].copy()
    if not pd.DatetimeIndex(price.index).equals(pd.DatetimeIndex(times["signal_date"])):
        raise ValueError(f"QQQ candles and signal trading dates disagree in {window}")
    curve = data["equity_curves"].loc[start:end, list(names.values())].copy()
    if curve.isna().any().any() or not curve.index.equals(price.index):
        raise ValueError(f"Equity curves do not match trading dates in {window}")
    fill = data["fills"].loc[(data["fills"]["window"] == window)
                             & (data["fills"]["strategy"] == strategy)].copy()
    if (fill["symbol"] != "QLD").any():
        raise ValueError(f"Long-only fills unexpectedly contain another instrument in {window}")
    stats = data["ffn_stats"].set_index("metric").loc[:, list(names.values())]
    stats = stats.rename(columns={v: k for k, v in names.items()})
    return {"window": window, "price": price, "signal": times.set_index("signal_date"),
            "curves": curve.rename(columns={v: k for k, v in names.items()}),
            "fills": fill, "stats": stats, "names": names}


def pair_trades(fills: pd.DataFrame, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map QLD fills onto QQQ signal-date candles; never mistake QLD dollars for QQQ."""
    events = []
    closed = []
    open_position = None
    for fill in fills.sort_values("timestamp").to_dict("records"):
        date = pd.Timestamp(fill["timestamp"])
        if date not in prices.index:
            raise ValueError(f"Missing QQQ candle for trade at {date}")
        if fill["side"] not in ("buy", "sell"):
            raise ValueError(f"Invalid trade side {fill['side']}")
        event = {
            "date": date, "qqq": float(prices.loc[date, "QQQ_Close"]),
            "symbol": fill["symbol"], "side": fill["side"],
            "price": float(fill["fill_price"]), "qty": float(fill["quantity"]),
            "fee": float(fill["fee"]),
        }
        events.append(event)
        if fill["side"] == "buy":
            if open_position is not None:
                raise ValueError("Simultaneous trades are unsupported in single-position PSAR")
            open_position = event
        elif open_position is None:
            raise ValueError("Sell without prior buy")
        else:
            entry = open_position
            capital = entry["price"] * entry["qty"] + entry["fee"]
            proceeds = event["price"] * event["qty"] - event["fee"]
            ret = proceeds / capital - 1
            closed.append({
                "date": date, "entry_date": entry["date"],
                "entry_qqq": entry["qqq"], "exit_qqq": event["qqq"],
                "return_pct": 100 * ret, "pnl": proceeds - capital,
                "win": ret > 0,
                "symbol": fill["symbol"],
            })
            open_position = None
    return pd.DataFrame(events, columns=["date", "qqq", "symbol", "side", "price", "qty", "fee"]), pd.DataFrame(
        closed, columns=["date", "entry_date", "entry_qqq", "exit_qqq",
                         "return_pct", "pnl", "win", "symbol"]
    )


_METRICS = {"total_return": "Total Return", "cagr": "CAGR",
            "sharpe": "Sharpe", "max_drawdown": "Max Drawdown"}
_SERIES = ("strategy", "QLD", "QQQ")


def psar_config(*, show_volume: bool = False) -> ReportConfig:
    """Preserve the approved PSAR page while expressing all PSAR choices explicitly."""
    caution = "Open trades have an entry marker but no realized P/L dot. "
    caution += ("Volume: QQQ actual market volume, independent from archived backtest P/L."
                if show_volume else
                "Volume panel is optional and disabled for this strategy.")
    return ReportConfig(
        title="PSAR QLD / Cash · Case Study",
        page_title="PSAR QLD/Cash Backtest Case Study",
        subtitle=("Source: immutable backtest-lab CSV outputs · "
                  "Signal: QQQ Parabolic SAR · execution: QLD only · "
                  "5-year windows · same-bar look-ahead bias (not tradable performance)."),
        interaction_note=("Interactive: mouse wheel zoom, drag pan, box zoom, "
                          "hover date/price/PSAR/QLD fills. Trade spans are projected on QQQ prices "
                          "(QLD execution dollars are only in marker tooltips)."),
        caution=caution,
        signal_symbol="QQQ",
        execution_symbol="QLD",
        display_symbol="QQQ",
        price_title="QQQ OHLC / Parabolic SAR / QLD execution dates",
        equity_title="Equity | strategy vs buy-and-hold (FFN performance index, initial 100)",
        performance_heading="Period performance & buy-and-hold",
        raw_ffn_note=("Values are read verbatim from ffn_stats.csv; "
                      "decimal rates have not been silently converted to percentages."),
        pnl_net_label="Net $",
        price_currency="USD",
        series=(
            SeriesConfig("strategy", "PSAR QLD/Cash", PALETTE["strategy"], 2.2, "PSAR Long Only"),
            SeriesConfig("QLD", "QLD B&H", PALETTE["QLD"], 1.5, "QLD Buy & Hold"),
            SeriesConfig("QQQ", "QQQ B&H", PALETTE["QQQ"], 1.5, "QQQ Buy & Hold"),
        ),
        overlays=(
            OverlayConfig("up_psar", "PSAR UP", PSAR_UP_COLOR),
            OverlayConfig("down_psar", "PSAR DOWN", PSAR_DOWN_COLOR),
        ),
        price_hover_fields=(
            ("PSAR", "@psar_value{0.00}"),
            ("State", "@psar_direction"),
            ("Segment days", "@current_len"),
            ("Action", "@action"),
        ),
        show_volume=show_volume,
    )


def numeric_performance(frame: pd.DataFrame, window: str) -> pd.DataFrame:
    """Map source column names to the canonical, *numeric* four-metric matrix."""
    selected = frame.loc[frame["window"] == window]
    names = {
        "strategy": f"PSAR Long Only {window}",
        "QLD": f"QLD Buy & Hold {window}",
        "QQQ": f"QQQ Buy & Hold {window}",
    }
    if len(selected) != 3 or set(selected["strategy"]) != set(names.values()):
        raise ValueError(f"Expected three strategies for performance matrix {window}")
    ordered = selected.set_index("strategy").loc[list(names.values()), list(_METRICS)]
    numeric = ordered.rename(index={value: key for key, value in names.items()})
    numeric = numeric.T.rename(index=_METRICS)
    return numeric.loc[list(_METRICS.values()), list(_SERIES)].copy()


def _performance_matrix(frame: pd.DataFrame, window: str) -> pd.DataFrame:
    """Backward-compatible PSAR-specific table helper."""
    return performance_matrix(numeric_performance(frame, window), psar_config())


def to_report_period(block: dict[str, object],
                     performance_summary: pd.DataFrame | None = None) -> ReportPeriod:
    """Adapt one validated PSAR window, never recomputing any FFN results."""
    prices = block["price"].rename(columns={
        "QQQ_Open": "Open", "QQQ_High": "High",
        "QQQ_Low": "Low", "QQQ_Close": "Close", "QQQ_Volume": "Volume",
    }).copy()
    indicators = block["signal"][["psar_value", "psar_direction", "action", "current_len"]].copy()
    indicators["up_psar"] = indicators["psar_value"].where(indicators["psar_direction"] == "UP")
    indicators["down_psar"] = indicators["psar_value"].where(indicators["psar_direction"] == "DOWN")
    events, trades = pair_trades(block["fills"], block["price"])
    events = events.rename(columns={"qqq": "display_price"})
    trades = trades.rename(columns={
        "entry_qqq": "entry_display_price", "exit_qqq": "exit_display_price",
    })
    if performance_summary is None:
        performance = pd.DataFrame()  # compatibility chart-only call
    else:
        performance = numeric_performance(performance_summary, block["window"])
    return ReportPeriod(
        window=block["window"],
        prices=prices,
        equity=block["curves"].copy(),
        performance=performance,
        ffn_stats=block["stats"].reset_index().copy(),
        indicators=indicators,
        events=events,
        trades=trades,
    )


def build_psar_data(outputs: dict[str, pd.DataFrame]) -> ReportData:
    return ReportData(tuple(
        to_report_period(window_data(outputs, window), outputs["performance_summary"])
        for window in WINDOWS
    ))
