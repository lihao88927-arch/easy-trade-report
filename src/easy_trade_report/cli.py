from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from .analytics import analyze_imports
from .comtrade import ComtradeError, fetch_import_data, resolve_reporter
from .models import Reporter
from .report import render_report

DEFAULT_HS_CODES = ("8504", "8535", "8536", "8537")


def _hs_code(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"\d{2}|\d{4}|\d{6}", normalized):
        raise argparse.ArgumentTypeError("HS code must contain 2, 4, or 6 digits.")
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-trade-report",
        description="Generate a Markdown import-market report from official UN Comtrade data.",
    )
    parser.add_argument(
        "--country",
        required=True,
        help="Target reporter country: ISO3, UN numeric code, or official English name.",
    )
    parser.add_argument(
        "--hs",
        nargs="+",
        type=_hs_code,
        default=list(DEFAULT_HS_CODES),
        help="One or more 2/4/6-digit HS codes (default: 8504 8535 8536 8537).",
    )
    parser.add_argument("--end-year", type=int, default=date.today().year - 1)
    parser.add_argument("--years", type=int, default=5, help="Number of annual periods (default: 5).")
    parser.add_argument("--top", type=int, default=10, help="Top suppliers per product (default: 10).")
    parser.add_argument("--output", type=Path, help="Markdown output path.")
    parser.add_argument(
        "--raw-csv",
        type=Path,
        help="Optional path for the raw official-client response. Useful for audit/debugging.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        help="Rebuild a report from a previously saved official-client CSV without a new API call.",
    )
    parser.add_argument(
        "--api-key-env",
        default="COMTRADE_API_KEY",
        help="Environment variable containing the subscription key.",
    )
    parser.add_argument(
        "--source-label",
        help="Source name printed in the report. Auto-detected when omitted.",
    )
    return parser


def _default_output(country: str, end_year: int) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", country.casefold()).strip("-") or "market"
    return Path("reports") / f"generated-{slug}-{end_year}.md"


def _reporter_from_csv(data: pd.DataFrame, fallback: str) -> Reporter:
    if data.empty:
        raise ValueError("Input CSV is empty.")

    for column in ("reporterCode", "reporterISO", "reporterDesc"):
        if column not in data.columns:
            continue
        values = {
            re.sub(r"\.0$", "", str(value)).strip().casefold()
            for value in data[column].dropna()
            if str(value).strip()
        }
        if len(values) > 1:
            raise ValueError(f"Input CSV contains multiple reporters in {column}.")

    row = data.iloc[0]
    raw_code = row.get("reporterCode", "")
    raw_name = row.get("reporterDesc", "")
    raw_iso3 = row.get("reporterISO", "")
    code = fallback if pd.isna(raw_code) else re.sub(r"\.0$", "", str(raw_code)) or fallback
    name = fallback if pd.isna(raw_name) else str(raw_name).strip() or fallback
    iso3 = None if pd.isna(raw_iso3) else str(raw_iso3).strip() or None
    return Reporter(code=code, name=name, iso3=iso3)


def _looks_like_official_comtrade(data: pd.DataFrame) -> bool:
    markers = {"classificationCode", "partner2Code", "isAggregate", "refPeriodId"}
    return len(markers.intersection(data.columns)) >= 2


def run(args: argparse.Namespace) -> Path:
    if args.years < 2:
        raise ValueError("--years must be at least 2.")
    if args.top < 1:
        raise ValueError("--top must be at least 1.")

    years = tuple(range(args.end_year - args.years + 1, args.end_year + 1))
    if args.input_csv:
        if not args.input_csv.exists():
            raise ValueError(f"Input CSV does not exist: {args.input_csv}")
        data = pd.read_csv(args.input_csv)
        reporter = _reporter_from_csv(data, args.country)
        source_label = args.source_label or (
            "UN Comtrade official statistics via saved official-client response"
            if _looks_like_official_comtrade(data)
            else "User-supplied trade data / 用户提供的贸易数据"
        )
        source_url = (
            "https://github.com/uncomtrade/comtradeapicall"
            if _looks_like_official_comtrade(data)
            else None
        )
    else:
        reporter = resolve_reporter(args.country)
        api_key = os.getenv(args.api_key_env, "").strip()
        if not api_key:
            raise ValueError(
                f"Environment variable {args.api_key_env} is empty. Set it to your UN Comtrade key."
            )
        data = fetch_import_data(api_key, reporter, args.hs, years)
        source_label = args.source_label or "UN Comtrade official statistics via comtradeapicall"
        source_url = "https://github.com/uncomtrade/comtradeapicall"
    analyses = analyze_imports(data, args.hs, years, top_n=args.top)
    report = render_report(
        reporter,
        analyses,
        source_label=source_label,
        source_url=source_url,
    )

    output = args.output or _default_output(reporter.iso3 or reporter.name, args.end_year)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")

    if args.raw_csv:
        args.raw_csv.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(args.raw_csv, index=False, encoding="utf-8-sig")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = run(args)
    except (ValueError, ComtradeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "cancelled\n")
    print(f"Report written to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
