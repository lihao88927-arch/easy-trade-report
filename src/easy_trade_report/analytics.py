from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd

from .models import ProductAnalysis, Supplier, TrendPoint


def _growth(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return current / previous - 1


def _cagr(last: float, first: float, intervals: int) -> float | None:
    if first <= 0 or last < 0 or intervals <= 0:
        return None
    return math.pow(last / first, 1 / intervals) - 1


def _concentration_label(hhi: float) -> str:
    if hhi < 1500:
        return "low"
    if hhi <= 2500:
        return "moderate"
    return "high"


def _first_description(rows: pd.DataFrame, hs_code: str) -> str:
    if "cmdDesc" not in rows.columns:
        return f"HS {hs_code}"
    values = rows["cmdDesc"].dropna().astype(str)
    return values.iloc[0] if not values.empty else f"HS {hs_code}"


def analyze_imports(
    data: pd.DataFrame,
    hs_codes: Iterable[str],
    years: Iterable[int],
    top_n: int = 10,
) -> list[ProductAnalysis]:
    """Calculate trends, growth, suppliers, CR3/CR5, and HHI from Comtrade rows."""
    if data is None or data.empty:
        raise ValueError("Trade data is empty.")
    required = {"period", "cmdCode", "partnerCode", "partnerDesc", "primaryValue"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Trade data is missing required columns: {sorted(missing)}")
    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    requested_years = tuple(sorted({int(year) for year in years}))
    frame = data.copy()
    frame["_year"] = pd.to_numeric(frame["period"], errors="coerce").astype("Int64")
    frame["_hs"] = frame["cmdCode"].astype(str).str.replace(r"\.0$", "", regex=True)
    frame["_partner_code"] = (
        frame["partnerCode"].astype(str).str.replace(r"\.0$", "", regex=True)
    )
    frame["_value"] = pd.to_numeric(frame["primaryValue"], errors="coerce").fillna(0.0)

    results: list[ProductAnalysis] = []
    for raw_code in hs_codes:
        hs_code = str(raw_code)
        rows = frame[frame["_hs"] == hs_code].copy()
        if rows.empty:
            continue

        world_rows = rows[rows["_partner_code"] == "0"]
        bilateral_rows = rows[rows["_partner_code"] != "0"]
        world_by_year = world_rows.groupby("_year", dropna=True)["_value"].sum()
        bilateral_by_year = bilateral_rows.groupby("_year", dropna=True)["_value"].sum()

        values_by_year: dict[int, float] = {}
        source = "World aggregate"
        for year in requested_years:
            if year in world_by_year.index:
                values_by_year[year] = float(world_by_year.loc[year])
            elif year in bilateral_by_year.index:
                values_by_year[year] = float(bilateral_by_year.loc[year])
                source = "sum of bilateral suppliers"

        if not values_by_year:
            continue

        available_years = sorted(values_by_year)
        first_year = available_years[0]
        latest_year = available_years[-1]
        first_value = values_by_year[first_year]
        latest_value = values_by_year[latest_year]

        trend: list[TrendPoint] = []
        previous: float | None = None
        for year in requested_years:
            value = values_by_year.get(year)
            yoy = _growth(value, previous) if value is not None and previous is not None else None
            trend.append(TrendPoint(year=year, import_value_usd=value, yoy_growth=yoy))
            if value is not None:
                previous = value

        latest_yoy = next(point.yoy_growth for point in reversed(trend) if point.year == latest_year)
        total_growth = _growth(latest_value, first_value)
        compound_growth = _cagr(latest_value, first_value, latest_year - first_year)

        latest_rows = bilateral_rows[bilateral_rows["_year"] == latest_year].copy()
        group_columns = ["_partner_code", "partnerDesc"]
        if "partnerISO" in latest_rows.columns:
            latest_rows["partnerISO"] = latest_rows["partnerISO"].fillna("").astype(str)
            group_columns.append("partnerISO")
        suppliers_frame = (
            latest_rows.groupby(group_columns, dropna=False, as_index=False)["_value"]
            .sum()
            .sort_values("_value", ascending=False)
        )
        supplier_total = float(suppliers_frame["_value"].sum())
        if supplier_total <= 0:
            raise ValueError(f"HS {hs_code} has no positive supplier values in {latest_year}.")
        suppliers_frame["_share"] = suppliers_frame["_value"] / supplier_total

        all_shares = suppliers_frame["_share"]
        hhi = float((all_shares.pow(2).sum()) * 10000)
        cr3 = float(all_shares.head(3).sum())
        cr5 = float(all_shares.head(5).sum())
        coverage = supplier_total / latest_value if latest_value > 0 else None

        suppliers = tuple(
            Supplier(
                code=str(row["_partner_code"]),
                name=str(row["partnerDesc"]),
                iso3=(str(row.get("partnerISO", "")) or None),
                import_value_usd=float(row["_value"]),
                share=float(row["_share"]),
            )
            for _, row in suppliers_frame.head(top_n).iterrows()
        )

        results.append(
            ProductAnalysis(
                hs_code=hs_code,
                description=_first_description(rows, hs_code),
                requested_years=requested_years,
                trend=tuple(trend),
                latest_year=latest_year,
                latest_import_value_usd=latest_value,
                first_available_year=first_year,
                first_available_value_usd=first_value,
                cagr=compound_growth,
                total_growth=total_growth,
                latest_yoy_growth=latest_yoy,
                suppliers=suppliers,
                hhi=hhi,
                concentration_label=_concentration_label(hhi),
                cr3=cr3,
                cr5=cr5,
                supplier_coverage=coverage,
                trend_source=source,
            )
        )

    if not results:
        raise ValueError("None of the requested HS codes had usable data.")
    return results

