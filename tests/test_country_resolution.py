import pandas as pd

from easy_trade_report.comtrade import resolve_reporter_from_dataframe

REFERENCE = pd.DataFrame(
    [
        {
            "reporterCode": 280,
            "reporterDesc": "Fed. Rep. of Germany (...1990)",
            "reporterCodeIsoAlpha3": "DEU",
            "entryEffectiveDate": "1900-01-01",
            "isGroup": False,
        },
        {
            "reporterCode": 276,
            "reporterDesc": "Germany",
            "reporterCodeIsoAlpha3": "DEU",
            "entryEffectiveDate": "1991-01-01",
            "isGroup": False,
        },
        {
            "reporterCode": 842,
            "reporterDesc": "USA",
            "reporterCodeIsoAlpha3": "USA",
            "entryEffectiveDate": "1981-01-01",
            "isGroup": False,
        },
    ]
)


def test_iso3_prefers_current_reporter() -> None:
    reporter = resolve_reporter_from_dataframe("DEU", REFERENCE)
    assert reporter.code == "276"
    assert reporter.name == "Germany"


def test_common_country_alias() -> None:
    reporter = resolve_reporter_from_dataframe("United States", REFERENCE)
    assert reporter.code == "842"


def test_chinese_country_alias() -> None:
    reporter = resolve_reporter_from_dataframe("德国", REFERENCE)
    assert reporter.code == "276"
