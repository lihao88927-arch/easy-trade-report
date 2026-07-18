---
name: generate-trade-market-report
description: Generate a verified bilingual Markdown import-market report from user-supplied CSV/XLSX trade data or from a target country plus HS codes using Easy Trade Report and the official UN Comtrade comtradeapicall package. Use when the user asks to generate a trade or import market report, analyze UN Comtrade data, select a market, create data-backed blog content, calculate five-year trends, growth, major suppliers, CR3/CR5, HHI, or market concentration, or refresh reports for HS 8504, 8535, 8536, or 8537.
---

# Generate Trade Market Report

Produce a complete report in one pass. Prefer acting from attached files and stated inputs over asking questions.

## Engine

Use `scripts/run_trade_report.ps1`. Pass `-EngineRoot` when working from a source checkout; otherwise let the wrapper use an installed `easy_trade_report` package. Do not create another UN Comtrade API client. Keep live data access inside the official `comtradeapicall` package.

## Input routing

1. Inspect the user message and attachments.
2. Select exactly one route:
   - **Official-response CSV:** If a CSV already contains Comtrade-style columns, use it with `-InputCsv`.
   - **General CSV/XLSX:** Read [references/input-contract.md](references/input-contract.md), inspect the data, normalize it to the required CSV schema with `scripts/normalize_trade_data.py`, then run with `-InputCsv -SourceLabel 'User-supplied trade data / 用户提供的贸易数据'` or a more precise label supplied by the user. Reject legacy `.xls`; ask for XLSX or CSV.
   - **Country + HS codes:** Run live mode. Use the country provided by the user and the provided HS codes. If no HS codes are given, default to `8504 8535 8536 8537`.
3. Default to five complete annual periods ending in the most recent reported year. If the user supplies explicit years, use them. For live mode, begin with the previous calendar year; if the target reporter has no usable data, move the end year back one year and explain the fallback.
4. Default to the top 10 suppliers unless the user specifies another number.

## Required output

Generate a Markdown report containing:

- five-year import trend;
- annual growth and CAGR;
- major suppliers and shares;
- CR3, CR5, HHI, and concentration label;
- methodology, data limitations, and source citation;
- Chinese and English headings.

Save final deliverables to the active task's `outputs/` directory when available. Otherwise save to the engine repository's `outputs/` directory. Use a descriptive file name containing the country and period.

When useful, also save a normalized or raw CSV beside the report, but never include credentials or credential sheets.

## Spreadsheet rules

For XLSX input, use the spreadsheet skill/tooling to inspect sheet names, headers, values, and formulas. Never read or export sheets named like `敏感凭证汇总`, `credentials`, `secrets`, `keys`, or `tokens` unless the user explicitly asks for credential administration. Do not put API keys into the normalized CSV or report. The normalizer requires the repository's `excel` extra (`openpyxl`) only for XLSX conversion.

When multiple sheets contain trade data, select the sheet with the required trade dimensions. If still ambiguous after inspection, prefer the largest clean table and state the selected sheet in the report handoff.

## Data validation

Before generating the report:

- confirm HS codes are 2, 4, or 6 digits;
- confirm annual periods are numeric years;
- confirm import values are numeric and non-negative;
- distinguish the World aggregate from bilateral supplier rows;
- avoid double counting aggregate and leaf/product-detail rows;
- preserve source labels such as `Other Asia, nes` rather than inventing a country;
- flag missing years instead of silently treating them as zero.

After generation:

1. Run the engine tests only if code was changed. Do not run them for an ordinary report job.
2. Check the report contains all required sections and at least one product result.
3. Verify the latest total, top supplier, CR3/CR5, and HHI against the normalized input or raw response.
4. Scan deliverables for credential-shaped values.
5. Return links to the Markdown report and any user-facing CSV/XLSX artifact.

## Failure handling

- Let the engine perform its bounded per-year/per-HS retries. Do not wrap it in another repeated retry loop.
- If a saved official-response CSV exists, switch to `-InputCsv` and rebuild offline.
- If the live engine still fails after its bounded retries, stop repeating. Report the failure and suggest using attached/exported data.
- Do not install a replacement API library or change the engine dependency without user confirmation.

## Typical triggers

- `生成贸易报告，国家德国，HS 8504 8537`
- `用这个Excel分析五年进口趋势和主要供应国`
- `把这份UN Comtrade CSV做成博客报告`
- `更新美国开关柜市场报告到最新五年`
- `用 $generate-trade-market-report 处理附件`
