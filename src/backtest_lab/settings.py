from __future__ import annotations

from dataclasses import dataclass

from dotenv import dotenv_values


@dataclass(frozen=True)
class ExecutionSettings:
    fee_rate: float = 0.00015
    slippage_bps: float = 0.0

    @classmethod
    def from_env(cls, path: str = ".env") -> "ExecutionSettings":
        values = dotenv_values(path)
        return cls(
            fee_rate=float(values.get("FEE_RATE") or cls.fee_rate),
            slippage_bps=float(values.get("SLIPPAGE_BPS") or cls.slippage_bps),
        )
