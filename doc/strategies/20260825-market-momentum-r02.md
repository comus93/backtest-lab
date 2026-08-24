# Market Momentum Correlation Pilot

Strategy ID: `market_momentum`
Revision: `r02`
Revision date: `2026-08-25`

## Purpose

Evaluate whether the 3M, 6M, and 12M relative-momentum strategies complement existing portfolio assets. This revision preserves r01 execution semantics and adds return-correlation analysis; r01 remains unchanged.

## Universe and period

Signal Universe: `SPY, QQQ, DIA, EWJ, EWY, MCHI, DAX, EWW, EIDO, INDY, EPHE`.

`VNAM`, `KTEC`, and `KSTR` are excluded. Use Yahoo Finance adjusted close, load sufficient history for 12M warm-up, and evaluate the active period `2016-07-01` through `2026-07-31`.

## Strategies

- Momentum Top 3: 3M, 6M, 12M only.
- Calendar-month momentum, ticker tie-break, Top 3 equal weights, and month-end signal / next-trading-day execution are identical to r01.
- SPY Buy & Hold is the benchmark.

## Correlation assets and conventions

Compare against `QQQ, SLV, GDX, AIA, XLF, XLE, EWW`; these assets do not alter the signal Universe.

All correlations are Pearson correlations of returns, never price or performance levels. Weekly and monthly observations use the last available observation in each calendar period. Pairwise calculations use only mutually available observations and retain `n_obs`; missing or insufficient observations are not imputed.

## Outputs

- `performance_summary.csv`
- `equity_curves.csv`
- `monthly_decisions.csv` for 3M/6M/12M
- `yearly_asset_correlation.csv`: `year,horizon,asset,correlation,n_obs` using weekly returns
- `overall_asset_correlation.csv`: `frequency,horizon,asset,correlation,n_obs` using weekly and monthly returns
- `yearly_constituent_correlation.csv`: `year,symbol_a,symbol_b,correlation,n_obs` using 12M constituents' weekly returns
- `yearly_constituents.csv`: `year,symbol,selected_months`

For each year, the 12M constituent set is the union of symbols selected in at least one monthly decision in that year.

## Boundaries

Implementation: `src/backtest_lab/strategies/market_momentum/r02.py`
Tests: `tests/strategies/market_momentum/test_r02.py`

No Core abstraction is added. Run outputs are stored under `runs/market_momentum/r02/<run_id>/`.
