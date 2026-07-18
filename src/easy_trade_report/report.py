from __future__ import annotations

from datetime import date

from .models import ProductAnalysis, Reporter


def _money(value: float | None) -> str:
    if value is None:
        return "N/A"
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"US${value / 1_000_000_000:,.2f}bn"
    if absolute >= 1_000_000:
        return f"US${value / 1_000_000:,.2f}m"
    if absolute >= 1_000:
        return f"US${value / 1_000:,.1f}k"
    return f"US${value:,.0f}"


def _percent(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.1%}" if signed else f"{value:.1%}"


def _concentration_text(label: str) -> str:
    return {
        "low": "low / 低集中",
        "moderate": "moderate / 中度集中",
        "high": "high / 高度集中",
    }[label]


def _market_direction(cagr: float | None) -> tuple[str, str]:
    if cagr is None:
        return "has insufficient data for a CAGR", "缺少足够数据计算 CAGR"
    if cagr >= 0:
        return "expanded", "扩张"
    return "contracted", "收缩"


def _sparkline(points: tuple) -> str:
    values = [point.import_value_usd for point in points if point.import_value_usd is not None]
    if not values:
        return ""
    if max(values) == min(values):
        return "▅" * len(values)
    blocks = "▁▂▃▄▅▆▇█"
    low, high = min(values), max(values)
    return "".join(blocks[round((value - low) / (high - low) * 7)] for value in values)


def _summary_sentence(item: ProductAnalysis) -> str:
    direction_en, direction_zh = _market_direction(item.cagr)
    leader = item.suppliers[0] if item.suppliers else None
    leader_text = (
        f"{leader.name} leads with {_percent(leader.share)}" if leader else "No supplier ranking available"
    )
    return (
        f"The market {direction_en} at a {_percent(item.cagr, signed=True)} CAGR from "
        f"{item.first_available_year} to {item.latest_year}; {leader_text}. "
        f"市场在该区间{direction_zh}，复合增速为 {_percent(item.cagr, signed=True)}，"
        f"供应格局为{_concentration_text(item.concentration_label)}。"
    )


def render_report(
    reporter: Reporter,
    analyses: list[ProductAnalysis],
    generated_on: date | None = None,
    source_label: str = "UN Comtrade official statistics",
    source_url: str | None = "https://github.com/uncomtrade/comtradeapicall",
) -> str:
    generated_on = generated_on or date.today()
    hs_list = ", ".join(item.hs_code for item in analyses)
    start_year = min(item.requested_years[0] for item in analyses)
    end_year = max(item.requested_years[-1] for item in analyses)

    source_text = source_label
    if source_url:
        source_text = f"[{source_label}]({source_url})"

    lines = [
        f"# {reporter.name} Electrical Equipment Import Market Report",
        "",
        f"> **中文标题：** {reporter.name} 电气设备进口市场报告  ",
        f"> **Products / 产品：** HS {hs_list}  ",
        f"> **Period / 时段：** {start_year}–{end_year}  ",
        f"> **Generated / 生成日期：** {generated_on.isoformat()}  ",
        f"> **Data source / 数据源：** {source_text}",
        "",
        "## Executive summary / 执行摘要",
        "",
        "| HS | Latest imports / 最新进口额 | CAGR | Latest YoY | "
        "Top supplier / 第一供应国 | HHI | Concentration / 集中度 |",
        "|---|---:|---:|---:|---|---:|---|",
    ]

    for item in analyses:
        leader = item.suppliers[0] if item.suppliers else None
        leader_text = f"{leader.name} ({_percent(leader.share)})" if leader else "N/A"
        lines.append(
            f"| {item.hs_code} | {_money(item.latest_import_value_usd)} ({item.latest_year}) "
            f"| {_percent(item.cagr, signed=True)} | {_percent(item.latest_yoy_growth, signed=True)} "
            f"| {leader_text} | {item.hhi:,.0f} | {_concentration_text(item.concentration_label)} |"
        )

    lines += [
        "",
        "### What the numbers say / 核心解读",
        "",
    ]
    for item in analyses:
        lines.append(f"- **HS {item.hs_code}:** {_summary_sentence(item)}")

    for item in analyses:
        lines += [
            "",
            f"## HS {item.hs_code} — {item.description}",
            "",
            "### Five-year import trend / 五年进口趋势",
            "",
            f"Trend / 趋势：`{_sparkline(item.trend)}`",
            "",
            "| Year / 年份 | Import value / 进口额 | YoY growth / 同比增速 |",
            "|---:|---:|---:|",
        ]
        for point in item.trend:
            lines.append(
                f"| {point.year} | {_money(point.import_value_usd)} "
                f"| {_percent(point.yoy_growth, signed=True)} |"
            )

        lines += [
            "",
            "### Growth indicators / 增长指标",
            "",
            f"- **CAGR / 复合年增长率:** {_percent(item.cagr, signed=True)} "
            f"({item.first_available_year}–{item.latest_year})",
            f"- **Total change / 区间总增幅:** {_percent(item.total_growth, signed=True)}",
            f"- **Latest YoY / 最新同比:** {_percent(item.latest_yoy_growth, signed=True)}",
            f"- **Trend total source / 趋势总额口径:** {item.trend_source}",
            "",
            f"### Major suppliers in {item.latest_year} / {item.latest_year} 年主要供应国",
            "",
            "| Rank | Supplier / 供应国 | Import value / 进口额 | Share / 份额 |",
            "|---:|---|---:|---:|",
        ]
        for rank, supplier in enumerate(item.suppliers, start=1):
            lines.append(
                f"| {rank} | {supplier.name} | {_money(supplier.import_value_usd)} "
                f"| {_percent(supplier.share)} |"
            )

        coverage_note = (
            _percent(item.supplier_coverage)
            if item.supplier_coverage is not None
            else "N/A"
        )
        lines += [
            "",
            "### Market concentration / 市场集中度",
            "",
            f"- **HHI:** {item.hhi:,.0f} — {_concentration_text(item.concentration_label)}",
            f"- **CR3:** {_percent(item.cr3)}",
            f"- **CR5:** {_percent(item.cr5)}",
            "- **Bilateral supplier coverage vs. reported World total / "
            f"双边供应国合计占世界总额:** {coverage_note}",
            "",
            "> HHI is calculated as the sum of squared supplier market shares multiplied by 10,000. "
            "This report uses the common thresholds: below 1,500 = low concentration; "
            "1,500–2,500 = moderate; above 2,500 = high.  ",
            "> HHI 按供应国份额平方和乘以 10,000 计算；低于 1,500 为低集中，"
            "1,500–2,500 为中度集中，高于 2,500 为高度集中。",
        ]

    lines += [
        "",
        "## Methodology and limitations / 方法与局限",
        "",
        "1. The target country is the **reporter** and trade flow is **imports** (`flowCode=M`). "
        "目标国家作为报告国，统计进口流向。",
        "2. In live mode, annual HS data are requested from UN Comtrade with the official "
        "`comtradeapicall` client; offline reports use the supplied CSV without making an API call. "
        "实时模式通过官方客户端取数；离线模式直接使用提供的 CSV。",
        "3. Import trend uses an explicit World aggregate where available; supplier rankings exclude "
        "partner code `0` (World) to avoid double counting.",
        "4. Latest-year HHI, CR3, and CR5 use bilateral supplier values. Differences between their sum "
        "and the World total can arise from confidential, special-category, rounding, or reporting records.",
        "5. Partner labels such as `Other Asia, nes` are reproduced exactly as supplied by the data source; "
        "the engine does not infer a country behind an aggregate or unspecified partner label.",
        "6. Data quality and revision schedules depend on the stated source. Use the report for screening "
        "and content research, then validate high-stakes commercial decisions with current primary sources.",
        "",
        "## Citation / 引用建议",
        "",
        f"> {source_label}, {reporter.name} annual imports, HS {hs_list}, "
        f"{start_year}–{end_year}, report generated {generated_on.isoformat()}.",
        "",
    ]
    return "\n".join(lines)
