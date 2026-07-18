# UN Comtrade solution selection / 方案选型

Research snapshot: **2026-07-18**. Repository statistics are a point-in-time snapshot and will change.

## Decision

Use [`uncomtrade/comtradeapicall`](https://github.com/uncomtrade/comtradeapicall) as the only network data-access layer. The report engine imports the published PyPI package and calls `getReference()` and `getFinalData()`; it does not recreate UN Comtrade URLs, authentication, retries, or response parsing.

This choice also matches the user's existing data-source workbook, which marks the official Python package as the first-choice source for product-level market sizing.

## Comparison

| Project | Snapshot | What it provides | Fit for this repository | Main risk |
|---|---:|---|---|---|
| [`uncomtrade/comtradeapicall`](https://github.com/uncomtrade/comtradeapicall) | 146 stars, 52 forks, MIT, latest commit 2026-06-11, PyPI 1.3.2 | Official Python library for final, tariff-line, metadata, bulk and reference APIs | **Selected.** Official ownership, current package, small dependency surface, direct HS/reporter/partner support | Thin error model; callers must validate empty frames and API limits |
| [`Moamen-Abdelkawy/InternationalTradeAnalyzer`](https://github.com/Moamen-Abdelkawy/InternationalTradeAnalyzer) | 2 stars, 1 fork, MIT, latest commit 2026-02-01 | Interactive CLI, BACI + Comtrade, charts, partner shares | Useful product inspiration, but not selected as a base | ~100 KB single application file, very large pinned environment, and a bundled client copy increase maintenance cost |
| [`Bodysbobb/trade-analysis`](https://github.com/Bodysbobb/trade-analysis) | 0 stars, MIT, latest commit 2025-10-29 | Multi-source Comtrade + World Bank + CEPII ETL | Useful reference for broader econometric workflows | Scope is much larger than a focused Markdown report; configuration-heavy and not a packaged report engine |
| [`tomszy91/comtrade_analysis`](https://github.com/tomszy91/comtrade_analysis) | 0 stars, MIT, latest commit 2026-04-02 | CSV cleaning, PostgreSQL schema and SQL analysis | Not suitable as the data-access base | Starts from a manually exported CSV and requires PostgreSQL/Docker; it does not solve API ingestion |

## Why this architecture is reliable

1. **Official client boundary.** UN Comtrade request construction stays in the upstream package.
2. **Small application layer.** This repository owns only country resolution, data validation, analytical metrics, and Markdown rendering.
3. **Auditable metrics.** CAGR, YoY, supplier shares, CR3/CR5, and HHI live in pure functions with fixture-based tests.
4. **No credential artifacts.** Keys enter through an environment variable and are neither printed nor persisted.
5. **Portable output.** Markdown can be committed, published as a blog draft, converted to PDF, or used as a portfolio artifact.

## Source links

- Official repository: <https://github.com/uncomtrade/comtradeapicall>
- Official package index: <https://pypi.org/project/comtradeapicall/>
- UN Comtrade developer portal: <https://comtradedeveloper.un.org/>
- UN Comtrade Plus: <https://comtradeplus.un.org/>

