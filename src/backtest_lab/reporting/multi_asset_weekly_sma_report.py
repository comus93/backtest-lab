"""CLI: publish multi-asset 21-week SMA run into a separate Pages subdirectory."""
from __future__ import annotations

import argparse

from .adapters.multi_asset_weekly_sma import publish_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Completed run directory")
    parser.add_argument("--output", required=True, help="Output site directory")
    args = parser.parse_args()
    files = publish_run(args.run, args.output)
    print(f"research_report_files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
