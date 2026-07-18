from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest

from easy_trade_report.cli import run


def _offline_args(csv_path: Path, output: Path) -> Namespace:
    return Namespace(
        country="USA",
        hs=["8504"],
        end_year=2024,
        years=2,
        top=10,
        output=output,
        raw_csv=None,
        input_csv=csv_path,
        api_key_env="COMTRADE_API_KEY",
        source_label=None,
    )


def test_offline_csv_rejects_multiple_reporters(tmp_path: Path) -> None:
    csv_path = tmp_path / "mixed.csv"
    pd.DataFrame(
        [
            {
                "period": 2023,
                "reporterDesc": "USA",
                "cmdCode": "8504",
                "partnerCode": 0,
                "partnerDesc": "World",
                "primaryValue": 90,
            },
            {
                "period": 2023,
                "reporterDesc": "USA",
                "cmdCode": "8504",
                "partnerCode": 156,
                "partnerDesc": "China",
                "primaryValue": 90,
            },
            {
                "period": 2024,
                "reporterDesc": "USA",
                "cmdCode": "8504",
                "partnerCode": 0,
                "partnerDesc": "World",
                "primaryValue": 100,
            },
            {
                "period": 2024,
                "reporterDesc": "Germany",
                "cmdCode": "8504",
                "partnerCode": 156,
                "partnerDesc": "China",
                "primaryValue": 200,
            },
        ]
    ).to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="multiple reporters"):
        run(_offline_args(csv_path, tmp_path / "report.md"))
