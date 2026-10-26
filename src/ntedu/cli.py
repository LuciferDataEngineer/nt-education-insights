"""Command line entry point.

    python -m ntedu.cli transform
    python -m ntedu.cli quality
    python -m ntedu.cli analysis
    python -m ntedu.cli static
    python -m ntedu.cli all
"""

from __future__ import annotations

import argparse
import logging
import sys

from ntedu.gold import build_gold
from ntedu.quality import run_quality
from ntedu.silver_abs import build_abs_silver
from ntedu.silver_acara import build_acara_silver
from ntedu.silver_ctg import build_ctg_silver
from ntedu.silver_naplan import build_naplan_silver
from ntedu.silver_nt import build_nt_silver
from ntedu.silver_rogs import build_rogs_silver


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def transform() -> None:
    nt = build_nt_silver()
    acara = build_acara_silver()
    build_naplan_silver()
    build_rogs_silver()
    build_abs_silver()
    build_ctg_silver()
    build_gold(nt["nt_school_attendance"], acara["acara_school_profile_nt"])


def analysis() -> None:
    from ntedu.analysis import run_analysis

    run_analysis()


def static() -> None:
    from ntedu.static_dashboard import build_static_dashboard

    build_static_dashboard()


def main(argv: list[str] | None = None) -> None:
    _configure_logging()
    parser = argparse.ArgumentParser(description="NT school education pipeline")
    parser.add_argument(
        "command",
        choices=["transform", "quality", "analysis", "static", "all"],
    )
    args = parser.parse_args(argv)
    if args.command in {"transform", "all"}:
        transform()
    if args.command in {"quality", "all"}:
        run_quality()
    if args.command in {"analysis", "all"}:
        analysis()
    if args.command in {"static", "all"}:
        static()


if __name__ == "__main__":
    main()
