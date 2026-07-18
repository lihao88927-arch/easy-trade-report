from pathlib import Path

import pandas as pd
import pytest

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


def test_missing_calendar_year_does_not_become_yoy() -> None:
    data = pd.DataFrame(
        [
            {"period": 2021, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 100},
            {"period": 2021, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 100},
            {"period": 2023, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 121},
            {"period": 2023, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 121},
        ]
    )

    result = analyze_imports(data, ["8504"], [2021, 2022, 2023])[0]
    assert result.trend[-1].yoy_growth is None


def test_hs6_rows_roll_up_to_requested_hs4() -> None:
    data = pd.DataFrame(
        [
            {"period": 2023, "cmdCode": "850421", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 50},
            {"period": 2023, "cmdCode": "850421", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 50},
            {"period": 2024, "cmdCode": "850421", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 60},
            {"period": 2024, "cmdCode": "850421", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 60},
        ]
    )

    result = analyze_imports(data, ["8504"], [2023, 2024])[0]
    assert result.latest_import_value_usd == 60
    assert result.suppliers[0].name == "China"


def test_exact_aggregate_rows_take_precedence_over_children() -> None:
    data = pd.DataFrame(
        [
            {"period": 2023, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 100},
            {"period": 2023, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 100},
            {"period": 2023, "cmdCode": "850421", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 40},
            {"period": 2023, "cmdCode": "850421", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 40},
            {"period": 2024, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 120},
            {"period": 2024, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 120},
            {"period": 2024, "cmdCode": "850421", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 50},
            {"period": 2024, "cmdCode": "850421", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 50},
        ]
    )

    result = analyze_imports(data, ["8504"], [2023, 2024])[0]
    assert result.latest_import_value_usd == 120


def test_rollup_uses_one_finest_level_per_year_and_partner() -> None:
    data = pd.DataFrame(
        [
            {"period": 2024, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 100},
            {"period": 2024, "cmdCode": "850421", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 40},
            {"period": 2024, "cmdCode": "850422", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 60},
            {"period": 2024, "cmdCode": "850421", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 40},
            {"period": 2024, "cmdCode": "850422", "partnerCode": 276, "partnerDesc": "Germany", "primaryValue": 60},
        ]
    )

    result = analyze_imports(data, ["85"], [2024])[0]
    assert result.latest_import_value_usd == 100
    assert sum(supplier.import_value_usd for supplier in result.suppliers) == 100


def test_exact_duplicate_rows_are_not_double_counted() -> None:
    rows = [
        {"period": 2024, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 100},
        {"period": 2024, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 100},
    ]
    data = pd.DataFrame(rows + rows)

    result = analyze_imports(data, ["8504"], [2024])[0]
    assert result.latest_import_value_usd == 100
    assert result.suppliers[0].import_value_usd == 100


def test_invalid_trade_value_is_rejected() -> None:
    data = pd.DataFrame(
        [
            {"period": 2023, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": "bad"},
            {"period": 2023, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 50},
            {"period": 2024, "cmdCode": "8504", "partnerCode": 0, "partnerDesc": "World", "primaryValue": 60},
            {"period": 2024, "cmdCode": "8504", "partnerCode": 156, "partnerDesc": "China", "primaryValue": 60},
        ]
    )

    with pytest.raises(ValueError, match="primaryValue"):
        analyze_imports(data, ["8504"], [2023, 2024])
