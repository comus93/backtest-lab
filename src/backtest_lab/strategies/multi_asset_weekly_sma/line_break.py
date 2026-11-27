"""Confirmed 3-Line Break constructed only from daily reference closes.

Rules follow the traditional line-break drawing conventions:
- New line in same direction when the next close exceeds the latest line close.
- Reversal only when close breaks the opposite extreme of the last N
  *confirmed lines*, not of the last N trading days.
- No new line = keep the previous confirmed direction. No projected bars.
- Reversal lines begin at the prior line's inner end (open), to keep their
  price range consistent with traditional line-break drawing.
"""
from __future__ import annotations

import math

import pandas as pd

DEFAULT_REVERSAL_LINES = 3


def daily_line_break_signals(
    reference_close: pd.Series, reversal_lines: int = DEFAULT_REVERSAL_LINES
) -> pd.DataFrame:
    """Produce one observable state per input daily close; never look ahead.

    Output direction is 1 (up), -1 (down), or 0 before the first confirmed
    line. A bar forms only on a close extension or an N-line reversal.
    Days with no new line preserve direction and contain formed=False.
    """
    if not isinstance(reversal_lines, int) or isinstance(reversal_lines, bool) or reversal_lines < 2:
        raise ValueError("reversal_lines must be an integer >= 2")
    if not isinstance(reference_close.index, pd.DatetimeIndex):
        raise ValueError("reference_close requires DatetimeIndex")
    closes = reference_close.dropna().sort_index().astype(float)
    if closes.empty or closes.index.has_duplicates:
        raise ValueError("reference close must be nonempty with unique dates")
    if any(not math.isfinite(float(c)) or c <= 0 for c in closes):
        raise ValueError("reference close must be finite and positive")

    baseline = float(closes.iloc[0])
    # Each confirmed line is (open, close, direction); confirmed only on close.
    lines: list[tuple[float, float, int]] = []
    rows: list[dict] = []
    for date, price in closes.items():
        close = float(price)
        formed = False
        reversed_line = False
        upper = lower = float("nan")
        if not lines:
            if close != baseline:
                direction = 1 if close > baseline else -1
                lines.append((baseline, close, direction))
                formed = True
        else:
            last_open, last_close, direction = lines[-1]
            previous = lines[-reversal_lines:]
            upper = max(max(a, b) for a, b, _ in previous)
            lower = min(min(a, b) for a, b, _ in previous)
            if direction == 1:
                if close > last_close:
                    lines.append((last_close, close, 1))
                    formed = True
                elif close < lower:
                    # The down-line starts at the latest up-line's low.
                    lines.append((last_open, close, -1))
                    formed = reversed_line = True
            else:
                if close < last_close:
                    lines.append((last_close, close, -1))
                    formed = True
                elif close > upper:
                    # The up-line starts at the latest down-line's high.
                    lines.append((last_open, close, 1))
                    formed = reversed_line = True
        if lines:
            current_open, current_close, direction = lines[-1]
        else:
            current_open = current_close = float("nan")
            direction = 0
        rows.append({
            "signal_date": date,
            "reference_close": close,
            "direction": direction,
            "line_formed": formed,
            "reversal": reversed_line,
            "line_open": current_open,
            "line_close": current_close,
            "prior_line_high": upper,
            "prior_line_low": lower,
            "confirmed_lines": len(lines),
        })
    return pd.DataFrame(rows).set_index("signal_date")
