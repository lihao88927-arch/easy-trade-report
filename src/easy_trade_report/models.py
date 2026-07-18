from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reporter:
    code: str
    name: str
    iso3: str | None = None


@dataclass(frozen=True)
class TrendPoint:
    year: int
    import_value_usd: float | None
    yoy_growth: float | None


@dataclass(frozen=True)
class Supplier:
    code: str
    name: str
    iso3: str | None
    import_value_usd: float
    share: float


@dataclass(frozen=True)
class ProductAnalysis:
    hs_code: str
    description: str
    requested_years: tuple[int, ...]
    trend: tuple[TrendPoint, ...]
    latest_year: int
    latest_import_value_usd: float
    first_available_year: int
    first_available_value_usd: float
    cagr: float | None
    total_growth: float | None
    latest_yoy_growth: float | None
    suppliers: tuple[Supplier, ...]
    hhi: float
    concentration_label: str
    cr3: float
    cr5: float
    supplier_coverage: float | None
    trend_source: str

