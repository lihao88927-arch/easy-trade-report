from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from time import sleep as _retry_sleep
from typing import Any

import pandas as pd
import requests
import urllib3
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .models import Reporter


class ComtradeError(RuntimeError):
    """Raised when the official UN Comtrade package cannot return usable data."""


MAX_RECORDS = 100_000
TRANSIENT_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    urllib3.exceptions.HTTPError,
)


COUNTRY_ALIASES = {
    "america": "USA",
    "u.s.": "USA",
    "u.s.a.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "uk": "GBR",
    "united kingdom": "GBR",
    "south korea": "KOR",
    "russia": "RUS",
    "vietnam": "VNM",
    "中国": "CHN",
    "美国": "USA",
    "德国": "DEU",
    "英国": "GBR",
    "法国": "FRA",
    "意大利": "ITA",
    "西班牙": "ESP",
    "日本": "JPN",
    "韩国": "KOR",
    "越南": "VNM",
    "印度": "IND",
    "印度尼西亚": "IDN",
    "印尼": "IDN",
    "墨西哥": "MEX",
    "加拿大": "CAN",
    "巴西": "BRA",
    "澳大利亚": "AUS",
    "俄罗斯": "RUS",
    "土耳其": "TUR",
    "沙特阿拉伯": "SAU",
    "沙特": "SAU",
    "阿联酋": "ARE",
    "南非": "ZAF",
    "埃及": "EGY",
}


def _official_package():
    try:
        import comtradeapicall
    except ImportError as exc:  # pragma: no cover - depends on environment setup
        raise ComtradeError(
            "comtradeapicall is not installed. Run: python -m pip install -e ."
        ) from exc
    return comtradeapicall


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def resolve_reporter_from_dataframe(country: str, reference: pd.DataFrame) -> Reporter:
    """Resolve a reporter without making network calls, making the logic unit-testable."""
    if reference is None or reference.empty:
        raise ComtradeError("The UN Comtrade reporter reference is empty.")

    query = country.strip()
    if not query:
        raise ValueError("Country must not be empty.")

    frame = reference.copy()
    required = {"reporterCode", "reporterDesc"}
    missing = required - set(frame.columns)
    if missing:
        raise ComtradeError(f"Reporter reference is missing columns: {sorted(missing)}")

    frame["_code"] = frame["reporterCode"].astype(str).str.replace(r"\.0$", "", regex=True)
    frame["_desc_norm"] = frame["reporterDesc"].map(_clean_text)
    frame["_text_norm"] = frame.get("text", frame["reporterDesc"]).map(_clean_text)
    if "reporterCodeIsoAlpha3" in frame.columns:
        frame["_iso3"] = frame["reporterCodeIsoAlpha3"].fillna("").astype(str).str.upper()
    else:
        frame["_iso3"] = ""

    if "isGroup" in frame.columns:
        group_flag = frame["isGroup"]
        if group_flag.dtype == object:
            group_flag = group_flag.fillna("").astype(str).str.casefold().isin({"true", "1", "yes"})
        else:
            group_flag = group_flag.fillna(False).astype(bool)
        frame = frame[~group_flag]

    normalized = _clean_text(query)
    alias = COUNTRY_ALIASES.get(normalized) or COUNTRY_ALIASES.get(query)
    upper = alias or query.upper()

    candidates = frame[frame["_code"] == query]
    if candidates.empty:
        candidates = frame[frame["_iso3"] == upper]
    if candidates.empty:
        candidates = frame[(frame["_desc_norm"] == normalized) | (frame["_text_norm"] == normalized)]

    if candidates.empty:
        suggestions = frame[
            frame["_desc_norm"].str.contains(re.escape(normalized), regex=True, na=False)
        ]["reporterDesc"].drop_duplicates().head(5).tolist()
        hint = f" Possible matches: {', '.join(suggestions)}." if suggestions else ""
        raise ValueError(f"Country '{country}' was not found in the UN Comtrade reporter list.{hint}")

    # Prefer current entities over historical entries such as "(...1990)".
    candidates = candidates.copy()
    candidates["_historical"] = candidates["reporterDesc"].astype(str).str.contains(
        r"\(\.\.\.|\(.*\d{4}", regex=True, na=False
    )
    if "entryEffectiveDate" in candidates.columns:
        candidates["_effective"] = pd.to_datetime(
            candidates["entryEffectiveDate"], errors="coerce"
        )
    else:
        candidates["_effective"] = pd.NaT
    selected = candidates.sort_values(
        ["_historical", "_effective", "reporterCode"], ascending=[True, False, False]
    ).iloc[0]

    iso3 = selected["_iso3"] or None
    return Reporter(code=str(selected["_code"]), name=str(selected["reporterDesc"]), iso3=iso3)


def resolve_reporter(country: str) -> Reporter:
    """Resolve a country using the official package's reporter reference."""
    package = _official_package()
    reference = package.getReference("reporter")
    return resolve_reporter_from_dataframe(country, reference)


def _missing_response(value: object) -> bool:
    return value is None or (isinstance(value, pd.DataFrame) and value.empty)


def _call_with_retry(operation: Callable[[], Any], context: str) -> Any:
    retrying = Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=20),
        retry=(
            retry_if_exception_type(TRANSIENT_EXCEPTIONS)
            | retry_if_result(_missing_response)
        ),
        sleep=_retry_sleep,
        reraise=True,
    )
    try:
        return retrying(operation)
    except RetryError as exc:
        raise ComtradeError(f"UN Comtrade returned no usable response after 3 attempts for {context}.") from exc
    except TRANSIENT_EXCEPTIONS as exc:
        raise ComtradeError(f"UN Comtrade request failed after 3 attempts for {context}: {exc}") from exc


def _query_kwargs(reporter: Reporter, year: int, hs_code: str) -> dict[str, object]:
    return {
        "typeCode": "C",
        "freqCode": "A",
        "clCode": "HS",
        "period": str(year),
        "reporterCode": reporter.code,
        "cmdCode": hs_code,
        "flowCode": "M",
        "partnerCode": None,
        "partner2Code": None,
        "customsCode": None,
        "motCode": None,
        "aggregateBy": None,
        "breakdownMode": "classic",
    }


def _response_count(value: object, context: str) -> int:
    frame = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
    if frame.empty or "count" not in frame.columns:
        raise ComtradeError(f"UN Comtrade returned an invalid count response for {context}.")
    try:
        count = int(frame.iloc[0]["count"])
    except (TypeError, ValueError) as exc:
        raise ComtradeError(f"UN Comtrade returned a non-numeric record count for {context}.") from exc
    if count < 0:
        raise ComtradeError(f"UN Comtrade returned a negative record count for {context}.")
    return count


def _validate_chunk(data: pd.DataFrame, reporter: Reporter, year: int, hs_code: str) -> None:
    context = f"{reporter.name}, HS {hs_code}, {year}"
    required = {"period", "cmdCode", "partnerCode", "partnerDesc", "primaryValue"}
    missing = required - set(data.columns)
    if missing:
        raise ComtradeError(f"UN Comtrade response is missing columns {sorted(missing)} for {context}.")

    periods = pd.to_numeric(data["period"], errors="coerce").dropna().astype(int).unique()
    if len(periods) != 1 or int(periods[0]) != year:
        raise ComtradeError(f"UN Comtrade returned an unexpected period for {context}.")
    products = data["cmdCode"].astype(str).str.replace(r"\.0$", "", regex=True)
    if not products.str.startswith(hs_code).all():
        raise ComtradeError(f"UN Comtrade returned an unexpected HS code for {context}.")
    if "reporterCode" in data.columns:
        reporters = data["reporterCode"].astype(str).str.replace(r"\.0$", "", regex=True)
        if not reporters.eq(reporter.code).all():
            raise ComtradeError(f"UN Comtrade returned an unexpected reporter for {context}.")


def fetch_import_data(
    api_key: str,
    reporter: Reporter,
    hs_codes: Iterable[str],
    years: Iterable[int],
) -> pd.DataFrame:
    """Fetch annual imports exclusively through the official comtradeapicall package."""
    if not api_key:
        raise ValueError("A UN Comtrade subscription key is required.")

    package = _official_package()
    requested_years = tuple(sorted({int(year) for year in years}))
    requested_products = tuple(dict.fromkeys(str(code) for code in hs_codes))
    chunks: list[pd.DataFrame] = []

    for year in requested_years:
        for hs_code in requested_products:
            context = f"{reporter.name}, HS {hs_code}, {year}"
            kwargs = _query_kwargs(reporter, year, hs_code)
            count_response = _call_with_retry(
                lambda kwargs=kwargs: package.getCountFinalData(api_key, **kwargs),
                f"record count: {context}",
            )
            count = _response_count(count_response, context)
            if count == 0:
                continue
            if count > MAX_RECORDS:
                raise ComtradeError(
                    f"UN Comtrade reports {count:,} records for {context}, exceeding the {MAX_RECORDS:,} record limit."
                )

            data_kwargs = {
                **kwargs,
                "maxRecords": MAX_RECORDS,
                "format_output": "JSON",
                "countOnly": False,
                "includeDesc": True,
            }
            response = _call_with_retry(
                lambda data_kwargs=data_kwargs: package.getFinalData(api_key, **data_kwargs),
                context,
            )
            chunk = response if isinstance(response, pd.DataFrame) else pd.DataFrame(response)
            if len(chunk) != count:
                raise ComtradeError(
                    f"UN Comtrade returned {len(chunk):,} of {count:,} expected records "
                    f"for {context}; refusing a truncated report."
                )
            _validate_chunk(chunk, reporter, year, hs_code)
            chunks.append(chunk)

    if not chunks:
        products = ",".join(requested_products)
        periods = ",".join(str(year) for year in requested_years)
        raise ComtradeError(f"No import records were returned for {reporter.name}, HS {products}, {periods}.")
    return pd.concat(chunks, ignore_index=True).drop_duplicates().reset_index(drop=True)
