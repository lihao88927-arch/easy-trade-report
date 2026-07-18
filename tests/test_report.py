from pathlib import Path

import pandas as pd

from easy_trade_report.analytics import analyze_imports
from easy_trade_report.models import Reporter
from easy_trade_report.report import render_report


def test_report_contains_required_sections() -> None:
    data = pd.read_csv(Path(__file__).parent / "fixtures" / "comtrade_sample.csv")
    analyses = analyze_imports(data, ["8504"], range(2020, 2025))
    report = render_report(Reporter("842", "USA", "USA"), analyses)

    assert "Five-year import trend / 五年进口趋势" in report
    assert "Major suppliers" in report
    assert "Market concentration / 市场集中度" in report
    assert "HHI" in report
    assert "comtradeapicall" in report


def test_report_discloses_unspecified_partner_labels() -> None:
    data = pd.read_csv(Path(__file__).parent / "fixtures" / "comtrade_sample.csv")
    analyses = analyze_imports(data, ["8504"], range(2020, 2025))
    report = render_report(Reporter("842", "USA", "USA"), analyses)
    assert "Other Asia, nes` are reproduced exactly" in report
