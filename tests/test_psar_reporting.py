"""Regression tests for immutable CSV-to-Bokeh case-study reporting."""
from pathlib import Path

import pandas as pd
import pytest

from backtest_lab.reporting.psar_report import (
    COLORS, WINDOWS, _make_charts, _monthly_candles, _performance_matrix,
    build_report, load_outputs, pair_trades, window_data,
)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "psar_segment_duration" / "r01" / "20261103-0002"


@pytest.fixture(scope="module")
def archived():
    return load_outputs(RUN)


@pytest.mark.parametrize("window", WINDOWS)
def test_window_mappings_and_dates_match(archived, window):
    block = window_data(archived, window)
    assert len(block["price"]) > 500
    assert block["price"].index.equals(block["curves"].index)
    assert block["signal"].index.equals(block["price"].index)
    assert not block["fills"].empty
    assert set(block["fills"]["symbol"]) == {"QLD"}
    assert list(block["stats"].columns) == ["strategy", "QLD", "QQQ"]


@pytest.mark.parametrize("window", WINDOWS)
def test_trade_event_projection_preserves_fills(archived, window):
    block = window_data(archived, window)
    events, complete = pair_trades(block["fills"], block["price"])
    assert len(events) == len(block["fills"])
    assert set(events["side"]) == {"buy", "sell"}
    assert (events["qqq"] > 0).all()
    assert (events["price"] > 0).all()
    assert len(complete) <= len(events) / 2
    assert (complete["entry_date"] <= complete["date"]).all()


def test_reject_window_without_its_independent_metrics(archived):
    bad = {k: v.copy() for k, v in archived.items()}
    bad["performance_summary"] = bad["performance_summary"].loc[
        bad["performance_summary"]["window"] != "2007-2011"
    ]
    with pytest.raises(ValueError, match="Expected strategy"):
        window_data(bad, "2007-2011")


def test_reject_synthetic_cross_symbol_position(archived):
    block = window_data(archived, "2007-2011")
    corrupt = block["fills"].copy()
    corrupt.loc[corrupt.index[0], "side"] = "sell"
    with pytest.raises(ValueError, match="Sell without"):
        pair_trades(corrupt, block["price"])


def test_generate_self_contained_bokeh_html(tmp_path):
    pytest.importorskip("bokeh")
    target = build_report(RUN, tmp_path / "site" / "index.html")
    text = target.read_text(encoding="utf-8")
    assert "PSAR QLD / Cash" in text
    assert "Cumulative return (%)" not in text
    assert "Profit / Loss" in text
    assert "QQQ Volume" not in text
    assert "Total Return" in text
    assert "QQQ OHLC" in text
    assert "Trade spans" in text
    assert "FFN result matrix" in text
    assert "QLD fill" in text
    assert "2022-2026" in text
    assert "Bokeh" in text
    assert len(text) > 500_000
    assert target.stat().st_size < 40_000_000


def test_period_performance_matrix_is_transposed(archived):
    comparison = _performance_matrix(archived["performance_summary"], WINDOWS[0])
    assert comparison.columns.tolist() == [
        "Metric", "PSAR Long Only", "QLD Buy & Hold", "QQQ Buy & Hold",
    ]
    assert comparison["Metric"].tolist() == ["Total Return", "CAGR", "Sharpe", "Max Drawdown"]
    assert comparison.loc[0, "PSAR Long Only"] == "+4.94%"
    assert comparison.loc[2, "PSAR Long Only"] == "0.145"


def test_monthly_overlay_distinguishes_up_and_down():
    dates = pd.to_datetime(["2026-01-02", "2026-01-05", "2026-02-02", "2026-02-03"])
    candles = pd.DataFrame({
        "QQQ_Open": [100, 106, 110, 103],
        "QQQ_High": [108, 112, 112, 105],
        "QQQ_Low": [99, 104, 102, 98],
        "QQQ_Close": [106, 111, 103, 99],
    }, index=dates)
    monthly = _monthly_candles(candles)
    assert monthly["color"].tolist() == [COLORS["monthly_bullish"], COLORS["monthly_bearish"]]
    assert monthly["high"].tolist() == [112.0, 112.0]
    assert monthly["low"].tolist() == [99.0, 98.0]
    assert monthly["top"].tolist() == [111.0, 110.0]
    assert monthly["bottom"].tolist() == [100.0, 99.0]


def test_chart_style_and_mouse_hover(archived):
    pytest.importorskip("bokeh")
    from bokeh.models import HoverTool

    charts = _make_charts(window_data(archived, WINDOWS[0]))
    assert len(charts.children) == 4  # Equity, Profit/Loss, drawdown, price
    equity, profit, drawdown, price = charts.children
    assert profit.title.text == "Profit / Loss"
    assert drawdown.title.text == "Strategy drawdown (%)"
    hover = [tool for tool in equity.tools if isinstance(tool, HoverTool)]
    assert not hover  # One CustomJS nearest-line tooltip, never three tooltips.
    move_callbacks = [callbacks for name, callbacks in equity.js_event_callbacks.items()
                      if "mousemove" in name]
    assert len(move_callbacks) == 1
    assert len(move_callbacks[0]) == 1
    assert "nearest.distance" in move_callbacks[0][0].code
    assert len(move_callbacks[0][0].args["lines"]) == 3
    assert all(fig.x_range is equity.x_range for fig in charts.children)
    assert all(fig.xgrid.grid_line_alpha == .20 for fig in charts.children)
    bars = [r for r in price.renderers if type(getattr(r, "glyph", None)).__name__ == "VBar"]
    assert len(bars) == 2  # translucent monthly + daily candlesticks
    assert bars[0].glyph.fill_alpha == .25
    assert bars[1].glyph.fill_color == "color"
    colors = bars[1].data_source.data["color"]
    assert set(colors) == {COLORS["bullish"], COLORS["bearish"]}
    spans = [r for r in price.renderers if type(getattr(r, "glyph", None)).__name__ == "MultiLine"]
    assert len(spans) == 1
    assert spans[0].glyph.line_width == 3
    assert spans[0].glyph.line_alpha == .80
    assert list(spans[0].glyph.line_dash) == [12, 9]
    assert COLORS["trade_span_loss"] == "#AD2960"
    assert COLORS["trade_span_profit"] == "#24954E"
    span_colors = set(spans[0].data_source.data["color"])
    assert span_colors <= {COLORS["trade_span_profit"], COLORS["trade_span_loss"]}


def test_psar_adapter_keeps_signal_display_and_fill_instruments_distinct(archived):
    from backtest_lab.reporting.adapters.psar import build_psar_data, psar_config

    report = build_psar_data(archived)
    config = psar_config()
    assert (config.signal_symbol, config.execution_symbol, config.display_symbol) == (
        "QQQ", "QLD", "QQQ",
    )
    report.validate(config)
    for period in report.periods:
        assert period.events["symbol"].eq("QLD").all()
        assert not period.events["price"].equals(period.events["display_price"])
        aligned = period.prices.loc[period.events["date"], "Close"].to_numpy()
        assert (period.events["display_price"].to_numpy() == aligned).all()
        assert len(period.trades) <= len(period.events) // 2
        for trade in period.trades.itertuples():
            assert trade.entry_display_price == period.prices.loc[trade.entry_date, "Close"]
            assert trade.exit_display_price == period.prices.loc[trade.date, "Close"]


def test_volume_panel_is_explicitly_optional(archived, tmp_path):
    pytest.importorskip("bokeh")
    block = window_data(archived, WINDOWS[0])
    assert len(_make_charts(block).children) == 4
    with pytest.raises(ValueError, match="QQQ_Volume"):
        _make_charts(block, show_volume=True)
    # Derived numeric volume below is only a plotting fixture, never used in backtest results.
    block["price"] = block["price"].copy()
    block["price"]["QQQ_Volume"] = 1000000.0
    result = _make_charts(block, show_volume=True)
    assert len(result.children) == 5
    price, volume = result.children[-2:]
    assert price.title.text.startswith("QQQ OHLC")
    assert volume.title.text == "QQQ Volume"
    assert volume.x_range is price.x_range
    assert volume.yaxis.axis_label == "QQQ Volume"
    assert any(type(getattr(r, "glyph", None)).__name__ == "VBar" for r in volume.renderers)
    # Report output can also be explicitly configured with a separate real data file.
    with pytest.raises(ValueError, match="Volume was requested"):
        build_report(RUN, tmp_path / "missing.html", show_volume=True)
