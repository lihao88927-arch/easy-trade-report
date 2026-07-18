# 易数据报告引擎 · Easy Trade Report

[English](#english) · [中文](#中文)

## 中文

这是一个面向开关柜、变压器出口业务的轻量市场报告生成器。输入目标国家和 HS 编码，即可从 UN Comtrade 官方统计中生成 Markdown 报告，包含：

- 五年进口趋势与逐年增速；
- 区间 CAGR 和总增幅；
- 最新年度主要供应国、进口额和份额；
- CR3、CR5 与 HHI 市场集中度；
- 中英双语表头、方法说明和引用建议。

默认产品范围：

| HS | 产品范围 |
|---|---|
| 8504 | 变压器、静态变流器及电感器 |
| 8535 | 电压超过 1,000V 的开关及保护设备 |
| 8536 | 电压不超过 1,000V 的开关及保护设备 |
| 8537 | 电气控制或配电用盘、板、柜等 |

### 为什么选择官方方案

数据接入只使用 UN Comtrade 官方维护的 [`uncomtrade/comtradeapicall`](https://github.com/uncomtrade/comtradeapicall)，本项目不自行拼装 HTTP 请求，也不复制第三方 API 客户端。2026-07-18 调研快照中，官方仓库为 146 星、52 forks、MIT 许可，且 2026-06 仍在更新；其他候选项目更适合作为分析案例，而不适合作为稳定的数据接入层。完整比较见 [docs/solution-selection.md](docs/solution-selection.md)。

### 安装

建议使用 Python 3.10–3.12：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

开发环境：

```powershell
python -m pip install -e ".[dev]"
```

### 配置密钥

在 [UN Comtrade Developer Portal](https://comtradedeveloper.un.org/) 创建订阅，然后只在环境变量中设置密钥：

```powershell
$env:COMTRADE_API_KEY = "你的订阅密钥"
```

不要把真实密钥写入 `.env.example`、代码、README、报告或 Git 提交。

### 生成报告

以美国、四个默认 HS 编码、2020–2024 五年为例：

```powershell
easy-trade-report `
  --country USA `
  --hs 8504 8535 8536 8537 `
  --end-year 2024 `
  --years 5 `
  --output reports/usa-electrical-equipment-2020-2024.md
```

### 在 GitHub 网页直接运行

仓库包含 `Generate Trade Market Report` GitHub Actions 工作流，无需在本地安装 Python：

1. 在仓库的 **Settings → Secrets and variables → Actions** 新建 Repository secret：`COMTRADE_API_KEY`。
2. 打开 **Actions → Generate Trade Market Report → Run workflow**。
3. 输入国家、HS 编码、结束年份、统计年数和供应国数量。
4. 运行完成后可直接在 Summary 查看报告，并在 Artifacts 下载 Markdown 与原始 CSV。

订阅密钥只作为 GitHub 加密 Secret 注入运行环境，不会出现在仓库或报告中。对于公开仓库，不要允许不受信任的 Pull Request 工作流访问该 Secret。

国家参数支持：ISO3（如 `DEU`）、UN 数字代码（如 `276`）、官方英文国名（如 `Germany`）或常用中文国名（如 `德国`）。

保存原始响应用于审计：

```powershell
easy-trade-report --country DEU --end-year 2024 `
  --raw-csv reports/germany-raw.csv
```

如果接口临时超时，可直接从之前保存的官方响应重建报告，不再消耗 API 调用：

```powershell
easy-trade-report --country DEU --end-year 2024 `
  --input-csv reports/germany-raw.csv `
  --output reports/germany-report.md
```

若目标国尚未上报最新年度，可用 `--end-year` 回退一年。不同国家发布节奏不同，不能把“无数据”直接理解为“无进口”。

### 指标口径

- 趋势总额优先使用 `partnerCode=0` 的 World 汇总行；若缺失，则回退为双边供应国合计。
- 供应国排名排除 World 行，避免重复计算。
- CAGR 使用首个和最后一个可用年度之间的实际年数。
- HHI = 各供应国份额平方和 × 10,000。
- 集中度阈值：HHI < 1,500 为低；1,500–2,500 为中度；> 2,500 为高。
- CR3/CR5 分别为前三/前五供应国份额之和。

UN Comtrade 是报告国提交的官方统计，最近年份可能修订；保密项、特殊伙伴类别与四舍五入可能造成双边合计和 World 总额存在差异。

### 项目结构

```text
src/easy_trade_report/
  comtrade.py      # 仅通过官方包取数和解析国家
  analytics.py     # 趋势、增速、供应国、CR3/CR5、HHI
  report.py        # Markdown 报告渲染
  cli.py           # 命令行入口
tests/             # 离线 fixture 与单元测试
docs/              # GitHub 方案选型记录
reports/           # 样例报告
```

### 测试

```powershell
python -m pytest
python -m ruff check .
```

样例：[美国电气设备进口报告](reports/sample-usa-electrical-equipment-2020-2024.md)。

---

## English

Easy Trade Report is a focused market-intelligence generator for exporters of transformers, switchgear, and electrical control equipment. Give it a target country and HS codes; it produces a Markdown report from official UN Comtrade statistics with:

- a five-year import trend and annual growth;
- CAGR and total period growth;
- major suppliers, values, and shares for the latest year;
- CR3, CR5, and Herfindahl-Hirschman Index (HHI);
- bilingual headings, methodology, limitations, and a suggested citation.

### Architecture decision

All network access goes through the official [`uncomtrade/comtradeapicall`](https://github.com/uncomtrade/comtradeapicall) PyPI package. This repository does not implement a replacement API client. The application layer is limited to reporter resolution, validation, analysis, and Markdown rendering. See [the comparison](docs/solution-selection.md).

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

For development:

```powershell
python -m pip install -e ".[dev]"
```

### Configure

Create a subscription in the [UN Comtrade Developer Portal](https://comtradedeveloper.un.org/) and expose the key only as an environment variable:

```powershell
$env:COMTRADE_API_KEY = "your-subscription-key"
```

### Run

```powershell
easy-trade-report `
  --country USA `
  --hs 8504 8535 8536 8537 `
  --end-year 2024 `
  --years 5 `
  --output reports/usa-electrical-equipment-2020-2024.md
```

### Run directly on GitHub

The included `Generate Trade Market Report` GitHub Actions workflow provides a browser form:

1. Add `COMTRADE_API_KEY` under **Settings → Secrets and variables → Actions**.
2. Open **Actions → Generate Trade Market Report → Run workflow**.
3. Enter the country, HS codes, end year, period count, and supplier count.
4. Read the report in the workflow summary or download the Markdown and raw CSV artifact.

The subscription key is injected as an encrypted GitHub Secret and is never committed to the repository.

`--country` accepts an ISO3 code, a UN numeric reporter code, or an official English country name. Use `--raw-csv` when an auditable copy of the official-client response is needed.

Use `--input-csv` to rebuild a report from a previously saved official-client response without making another API call.

### Metric definitions

- Trend totals prefer the reported World aggregate and fall back to summed bilateral suppliers.
- Supplier rankings exclude the World row.
- CAGR uses the actual interval between the first and last available years.
- HHI is the sum of squared supplier shares multiplied by 10,000.
- Concentration thresholds: below 1,500 low; 1,500–2,500 moderate; above 2,500 high.
- CR3 and CR5 are the combined shares of the top three and top five suppliers.

UN Comtrade data are official reporter-submitted statistics, but recent periods can be revised and reporting calendars vary. Treat the output as a market-screening and content-research artifact, then validate high-stakes decisions with current primary sources.

### Quality checks

```powershell
python -m pytest
python -m ruff check .
```

Example: [USA electrical equipment import report](reports/sample-usa-electrical-equipment-2020-2024.md).

## License

MIT. UN Comtrade data remain subject to the source's terms and citation requirements.
