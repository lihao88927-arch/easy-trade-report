from pathlib import Path

import pandas as pd

from easy_trade_report.analytics import analyze_imports

FIXTURE = Path(__file__).parent / "fixtures" / "comtrade_sample.csv"


def test_analyze_imports_calculates_growth_and_concentration() -> None:
    data = pd.read_csv(FIXTURE)
    result = analyze_imports(data, ["8504"], range(2020, 2025), top_n=3)[0]

    assert result.latest_year == 2024
    assert result.latest_import_value_usd == 146.41
    assert round(result.cagr or 0, 6) == 0.1
    assert round(result.latest_yoy_growth or 0, 6) == 0.1
    assert [supplier.name for supplier in result.suppliers] == ["China", "Mexico", "Germany"]
    assert round(result.cr3, 6) == 1.0
    assert round(result.hhi, 1) == 3800.0
    assert result.concentration_label == "high"


def test_world_total_is_not_double_counted() -> None:
    data = pd.read_csv(FIXTURE)
    result = analyze_imports(data, ["8504"], range(2020, 2025))[0]
    assert result.latest_import_value_usd == 146.41
    assert round(sum(s.import_value_usd for s in result.suppliers), 3) == 146.41

