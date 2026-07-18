from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from .models import Reporter


class ComtradeError(RuntimeError):
    """Raised when the official UN Comtrade package cannot return usable data."""


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
    periods = ",".join(str(year) for year in years)
    products = ",".join(hs_codes)
    data = package.getFinalData(
        api_key,
        typeCode="C",
        freqCode="A",
        clCode="HS",
        period=periods,
        reporterCode=reporter.code,
        cmdCode=products,
        flowCode="M",
        partnerCode=None,
        partner2Code=None,
        customsCode=None,
        motCode=None,
        maxRecords=100000,
        format_output="JSON",
        aggregateBy=None,
        breakdownMode="classic",
        countOnly=False,
        includeDesc=True,
    )
    if data is None:
        raise ComtradeError(
            "UN Comtrade returned no response. Check the key, rate limits, and query parameters."
        )
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    if data.empty:
        raise ComtradeError(
            f"No import records were returned for {reporter.name}, HS {products}, {periods}."
        )
    return data
