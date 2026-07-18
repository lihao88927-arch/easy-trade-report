from __future__ import annotations

from collections import defaultdict

import pandas as pd
import pytest

from easy_trade_report import comtrade
from easy_trade_report.comtrade import ComtradeError, fetch_import_data
from easy_trade_report.models import Reporter


class FakeComtradePackage:
    def __init__(self) -> None:
        self.count_calls: list[dict[str, object]] = []
        self.data_calls: list[dict[str, object]] = []
        self.attempts: defaultdict[tuple[str, str], int] = defaultdict(int)
        self.failures_before_success = 0
        self.count = 2

    def getCountFinalData(self, _api_key: str, **kwargs: object) -> pd.DataFrame:
        self.count_calls.append(kwargs)
        return pd.DataFrame([{"count": self.count}])

    def getFinalData(self, _api_key: str, **kwargs: object) -> pd.DataFrame | None:
        self.data_calls.append(kwargs)
        period = str(kwargs["period"])
        hs_code = str(kwargs["cmdCode"])
        key = (period, hs_code)
        self.attempts[key] += 1
        if self.attempts[key] <= self.failures_before_success:
            return None
        return pd.DataFrame(
            [
                {
                    "period": int(period),
                    "reporterCode": 842,
                    "cmdCode": hs_code,
                    "partnerCode": 0,
                    "partnerDesc": "World",
                    "primaryValue": 100,
                },
                {
                    "period": int(period),
                    "reporterCode": 842,
                    "cmdCode": hs_code,
                    "partnerCode": 156,
                    "partnerDesc": "China",
                    "primaryValue": 100,
                },
            ]
        )


def test_fetch_splits_requests_by_year_and_hs(monkeypatch: pytest.MonkeyPatch) -> None:
    package = FakeComtradePackage()
    monkeypatch.setattr(comtrade, "_official_package", lambda: package)

    result = fetch_import_data("secret", Reporter("842", "USA", "USA"), ["8504", "8537"], [2023, 2024])

    assert len(package.count_calls) == 4
    assert len(package.data_calls) == 4
    assert {(call["period"], call["cmdCode"]) for call in package.data_calls} == {
        ("2023", "8504"),
        ("2023", "8537"),
        ("2024", "8504"),
        ("2024", "8537"),
    }
    assert len(result) == 8


def test_fetch_retries_transient_empty_response_at_most_three_times(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = FakeComtradePackage()
    package.failures_before_success = 2
    monkeypatch.setattr(comtrade, "_official_package", lambda: package)
    monkeypatch.setattr(comtrade, "_retry_sleep", lambda _seconds: None)

    result = fetch_import_data("secret", Reporter("842", "USA", "USA"), ["8504"], [2024])

    assert len(result) == 2
    assert package.attempts[("2024", "8504")] == 3


def test_fetch_rejects_chunk_larger_than_api_record_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    package = FakeComtradePackage()
    package.count = 100_001
    monkeypatch.setattr(comtrade, "_official_package", lambda: package)

    with pytest.raises(ComtradeError, match="100,001.*100,000"):
        fetch_import_data("secret", Reporter("842", "USA", "USA"), ["8504"], [2024])

    assert package.data_calls == []


def test_fetch_stops_after_three_empty_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    package = FakeComtradePackage()
    package.failures_before_success = 3
    monkeypatch.setattr(comtrade, "_official_package", lambda: package)
    monkeypatch.setattr(comtrade, "_retry_sleep", lambda _seconds: None)

    with pytest.raises(ComtradeError, match="after 3 attempts"):
        fetch_import_data("secret", Reporter("842", "USA", "USA"), ["8504"], [2024])

    assert package.attempts[("2024", "8504")] == 3


def test_fetch_rejects_truncated_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    package = FakeComtradePackage()
    package.count = 3
    monkeypatch.setattr(comtrade, "_official_package", lambda: package)

    with pytest.raises(ComtradeError, match="2 of 3 expected records"):
        fetch_import_data("secret", Reporter("842", "USA", "USA"), ["8504"], [2024])
