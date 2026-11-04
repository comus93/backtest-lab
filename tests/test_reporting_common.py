"""Contract tests that use invented tickers, without adding a second strategy."""
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from backtest_lab.reporting import (
    OverlayConfig, ReportConfig, ReportData, ReportPeriod, SeriesConfig, render_report,
)
from backtest_lab.reporting.charts import build_charts
from backtest_lab.reporting.tables import performance_matrix


def sample(*, volume: bool = True) -> tuple[ReportData, ReportConfig]:
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    prices = pd.DataFrame({
        "Open": [10.0, 11.0, 12.0, 13.0],
        "High": [11.1, 12.1, 13.1, 14.1],
        "Low": [9.8, 10.8, 11.8, 12.8],
        "Close": [11.0, 12.0, 13.0, 14.0],
    }, index=dates)
    if volume:
        prices["Volume"] = [12_000, 16_000, 13_000, 11_000]
    equity = pd.DataFrame({
        "primary": [100, 102, 105, 109],
        "base": [100, 101, 104, 106],
    }, index=dates)
    performance = pd.DataFrame({
        "primary": [.09, .11, 1.12, -.04],
        "base": [.06, .07, 0.8, -.07],
    }, index=["Total Return", "CAGR", "Sharpe", "Max Drawdown"])
    ffn = pd.DataFrame({
        "metric": ["cagr", "max_drawdown"], "primary": [.11, -.04], "base": [.07, -.07],
    })
    period = ReportPeriod(window="2024", prices=prices, equity=equity,
                          performance=performance, ffn_stats=ffn)
    config = ReportConfig(
        title="Agnostic report", page_title="Agnostic",
        subtitle="Stand-alone FFN results", interaction_note="No PSAR required",
        caution="For testing only", signal_symbol="AAA",
        execution_symbol="BBB", display_symbol="CCC",
        price_title="CCC OHLC and executions",
        series=(
            SeriesConfig("primary", "Alpha", "#123456", 2.2, "Main Strategy"),
            SeriesConfig("base", "Reference", "#654321", 1.5, "Passive"),
        ),
        show_trades=False, show_monthly=False, show_volume=volume,
    )
    return ReportData((period,)), config


def test_agnostic_report_contract_and_render(tmp_path):
    pytest.importorskip("bokeh")
    data, config = sample()
    data.validate(config)
    chart = build_charts(data.periods[0], config)
    assert [fig.title.text for fig in chart.children] == [
        config.equity_title, config.pnl_title, config.drawdown_title,
        config.price_title, "CCC Volume",
    ]
    price, volume = chart.children[-2:]
    assert price.x_range is volume.x_range
    assert [type(renderer.glyph).__name__ for renderer in price.renderers
            if hasattr(renderer, "glyph")] == ["Segment", "VBar"]
    assert [type(renderer.glyph).__name__ for renderer in volume.renderers
            if hasattr(renderer, "glyph")] == ["VBar"]
    matrix = performance_matrix(data.periods[0].performance, config)
    assert matrix.columns.tolist() == ["Metric", "Main Strategy", "Passive"]
    assert matrix.loc[0, "Main Strategy"] == "+9.00%"
    assert matrix.loc[2, "Main Strategy"] == "1.120"
    before = data.periods[0].prices.copy(deep=True)
    result = render_report(data, config, tmp_path / "example.html")
    assert result.is_file() and result.stat().st_size > 100_000
    assert "CCC OHLC and executions" in result.read_text(encoding="utf-8")
    pd.testing.assert_frame_equal(data.periods[0].prices, before)


def test_indicator_marker_size_is_shared_across_overlays():
    pytest.importorskip("bokeh")
    data, config = sample(volume=False)
    period = data.periods[0]
    indicators = pd.DataFrame({
        "first": [10.0, 11.0, 12.0, 13.0],
        "second": [10.5, 11.5, 12.5, 13.5],
    }, index=period.prices.index)
    config = replace(config, indicator_marker_size=2, overlays=(
        OverlayConfig("first", "First", "#8C786A"),
        OverlayConfig("second", "Second", "#8B7F99"),
    ))
    price = build_charts(replace(period, indicators=indicators), config).children[-1]
    markers = [renderer.glyph for renderer in price.renderers
               if type(getattr(renderer, "glyph", None)).__name__ == "Scatter"]
    assert len(markers) == 2
    assert all(glyph.size == config.indicator_marker_size for glyph in markers)
    smaller = replace(config, indicator_marker_size=1)
    smaller_price = build_charts(replace(period, indicators=indicators), smaller).children[-1]
    assert all(renderer.glyph.size == 1 for renderer in smaller_price.renderers
               if type(getattr(renderer, "glyph", None)).__name__ == "Scatter")


def test_opaque_volume_is_a_opt_in_requirement():
    data, config = sample(volume=False)
    data.validate(replace(config, show_volume=False))
    with pytest.raises(ValueError, match="Volume"):
        data.validate(replace(config, show_volume=True))


def test_reject_misaligned_equity_or_missing_overlay():
    data, config = sample()
    period = data.periods[0]
    shifted = period.equity.copy()
    shifted.index = shifted.index + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="equity and price dates differ"):
        ReportData((replace(period, equity=shifted),)).validate(config)
    with pytest.raises(ValueError, match="missing overlay field"):
        data.validate(replace(config, overlays=(OverlayConfig("sma", "SMA", "#000000"),)))


def test_reject_duplicate_windows_and_series_keys():
    data, config = sample()
    with pytest.raises(ValueError, match="Duplicate report period"):
        ReportData((data.periods[0], data.periods[0])).validate(config)
    with pytest.raises(ValueError, match="unique"):
        data.validate(replace(config, series=(config.series[0], config.series[0])))


def test_reject_invalid_ohlc_and_nonfinite_metrics():
    data, config = sample()
    period = data.periods[0]
    bad_prices = period.prices.copy()
    bad_prices.loc[bad_prices.index[0], "High"] = 9.0
    with pytest.raises(ValueError, match="High is below"):
        ReportData((replace(period, prices=bad_prices),)).validate(config)
    bad_perf = period.performance.copy()
    bad_perf.iloc[0, 0] = float("nan")
    with pytest.raises(ValueError, match="non-finite FFN"):
        ReportData((replace(period, performance=bad_perf),)).validate(config)


def test_avoid_unrequested_monthly_or_volume_panels():
    pytest.importorskip("bokeh")
    data, config = sample(volume=False)
    config = replace(config, show_volume=False)
    plot = build_charts(data.periods[0], config)
    assert len(plot.children) == 4
    candles = plot.children[-1]
    assert len([r for r in candles.renderers
                if type(getattr(r, "glyph", None)).__name__ == "VBar"]) == 1
