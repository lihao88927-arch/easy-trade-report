from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

REQUIRED_TRADE_COLUMNS = {
    "period",
    "cmdCode",
    "partnerCode",
    "partnerDesc",
    "primaryValue",
}


TRADE_DATA_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(int, checks=pa.Check.in_range(1900, 2100), coerce=True),
        "cmdCode": pa.Column(
            str,
            checks=pa.Check.str_matches(r"^(?:\d{2}|\d{4}|\d{6})$"),
            coerce=True,
        ),
        "partnerCode": pa.Column(str, coerce=True),
        "partnerDesc": pa.Column(str, coerce=True),
        "primaryValue": pa.Column(float, checks=pa.Check.ge(0), coerce=True),
    },
    strict=False,
    coerce=False,
)


def validate_trade_data(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the analytical boundary without discarding source columns."""
    if data is None or data.empty:
        raise ValueError("Trade data is empty.")

    missing = REQUIRED_TRADE_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Trade data is missing required columns: {sorted(missing)}")

    frame = data.copy()
    frame["cmdCode"] = frame["cmdCode"].astype("string").str.replace(r"\.0$", "", regex=True).str.strip()
    frame["partnerCode"] = (
        frame["partnerCode"].astype("string").fillna("").str.replace(r"\.0$", "", regex=True).str.strip()
    )
    frame["partnerDesc"] = frame["partnerDesc"].astype("string").fillna("").str.strip()

    try:
        return TRADE_DATA_SCHEMA.validate(frame, lazy=True).drop_duplicates().reset_index(drop=True)
    except SchemaErrors as exc:
        columns = sorted(
            {
                str(column)
                for column in exc.failure_cases.get("column", pd.Series(dtype="object")).dropna()
            }
        )
        detail = ", ".join(columns) or "unknown fields"
        raise ValueError(f"Trade data validation failed for: {detail}.") from exc
