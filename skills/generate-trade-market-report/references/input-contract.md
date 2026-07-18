# Input contract

## Preferred UN Comtrade schema

The engine accepts a CSV with at least these columns:

| Field | Meaning |
|---|---|
| `period` | Annual year, such as `2024` |
| `reporterCode` | UN numeric reporter code |
| `reporterISO` | Reporter ISO3, if available |
| `reporterDesc` | Reporter name |
| `partnerCode` | UN partner code; `0` means World |
| `partnerISO` | Partner ISO3, if available |
| `partnerDesc` | Partner name |
| `cmdCode` | HS code |
| `cmdDesc` | Product description |
| `primaryValue` | Import value in current US dollars |

Optional but useful fields include `flowCode`, `flowDesc`, `isAggregate`, `isLeaf`, `aggrLevel`, and `classificationCode`.

## General-table aliases

The normalizer recognizes common English and Chinese aliases:

- year: `year`, `年份`, `年度`, `period`
- reporter: `reporter`, `reporter country`, `进口国`, `报告国`, `目标国家`
- partner: `partner`, `supplier`, `origin`, `供应国`, `来源国`, `贸易伙伴`
- HS code: `hs`, `hs code`, `商品编码`, `海关编码`
- product: `product`, `description`, `产品`, `商品名称`
- value: `trade value`, `import value`, `value usd`, `进口额`, `贸易额`, `金额`
- share: `share`, `market share`, `份额` (optional; the engine recalculates it from values)

## World total

Prefer an explicit World row with partner code `0`. If none exists, the analysis engine sums bilateral supplier values for the trend total. Never add the World row to bilateral supplier rows.

## Granularity

Use one row per year, reporter, HS code, and supplier after aggregation when possible. The engine prefers exact requested-level rows; otherwise it selects one finest descendant level per year and partner so aggregate rows and child rows are not added together.

## Missing data

Keep missing years as missing. Do not manufacture zero trade. Negative trade values are invalid for this workflow and require investigation.

## File formats

Accept CSV and XLSX. Legacy XLS is intentionally unsupported because it requires a separate parser; save it as XLSX or CSV before normalization.
