from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

ALIASES = {
    "period": ["period", "year", "年份", "年度"],
    "reporterDesc": ["reporterdesc", "reporter", "reporter country", "进口国", "报告国", "目标国家"],
    "reporterCode": ["reportercode", "reporter code", "报告国代码"],
    "reporterISO": ["reporteriso", "reporter iso", "报告国iso", "进口国iso"],
    "partnerDesc": ["partnerdesc", "partner", "supplier", "origin", "供应国", "来源国", "贸易伙伴"],
    "partnerCode": ["partnercode", "partner code", "供应国代码", "伙伴代码"],
    "partnerISO": ["partneriso", "partner iso", "供应国iso"],
    "cmdCode": ["cmdcode", "hs", "hs code", "hscode", "hs编码", "商品编码", "海关编码"],
    "cmdDesc": ["cmddesc", "product", "description", "产品", "商品名称"],
    "primaryValue": ["primaryvalue", "trade value", "import value", "value usd", "进口额", "贸易额", "金额"],
}


def normalize_header(value: object) -> str:
    return re.sub(r"[\s_\-/]+", " ", str(value).strip().casefold())


def find_columns(columns: list[object]) -> dict[str, object]:
    normalized = {normalize_header(column): column for column in columns}
    result: dict[str, object] = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            match = normalized.get(normalize_header(alias))
            if match is not None:
                result[target] = match
                break
    return result


def load_table(path: Path, sheet: str | None) -> pd.DataFrame:
    if path.suffix.casefold() == ".csv":
        return pd.read_csv(path)
    if path.suffix.casefold() == ".xlsx":
        if sheet and re.search(r"credentials|secrets|keys|tokens|敏感|凭证|密钥", sheet, re.I):
            raise ValueError("Refusing to normalize a credential-like sheet.")
        try:
            return pd.read_excel(path, sheet_name=sheet or 0, engine="openpyxl")
        except ImportError as exc:
            raise ValueError(
                "XLSX support requires openpyxl. Install the engine with: "
                "python -m pip install -e '.[excel]'"
            ) from exc
    if path.suffix.casefold() == ".xls":
        raise ValueError("Legacy XLS is not supported. Save the workbook as XLSX or CSV first.")
    raise ValueError("Input must be CSV or XLSX.")


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    mapping = find_columns(list(frame.columns))
    required = {"period", "reporterDesc", "partnerDesc", "cmdCode", "primaryValue"}
    missing = sorted(required - set(mapping))
    if missing:
        raise ValueError(f"Could not identify required fields: {missing}")

    output = pd.DataFrame({target: frame[source] for target, source in mapping.items()})
    output["period"] = pd.to_numeric(output["period"], errors="raise").astype(int)
    output["cmdCode"] = output["cmdCode"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    invalid_hs = ~output["cmdCode"].str.fullmatch(r"\d{2}|\d{4}|\d{6}")
    if invalid_hs.any():
        raise ValueError(f"Invalid HS codes found: {output.loc[invalid_hs, 'cmdCode'].unique().tolist()[:10]}")
    output["primaryValue"] = pd.to_numeric(output["primaryValue"], errors="raise")
    if (output["primaryValue"] < 0).any():
        raise ValueError("Negative import values are not supported.")

    for field, default in {
        "reporterCode": "",
        "reporterISO": "",
        "partnerCode": "",
        "partnerISO": "",
        "cmdDesc": "",
    }.items():
        if field not in output:
            output[field] = default

    for field in ("reporterCode", "reporterISO", "partnerCode", "partnerISO", "cmdDesc"):
        output[field] = output[field].astype("string").fillna("")

    world_mask = output["partnerDesc"].astype(str).str.strip().str.casefold().isin(
        {"world", "全球", "世界", "total", "all partners"}
    )
    output.loc[world_mask & output["partnerCode"].astype(str).str.strip().eq(""), "partnerCode"] = "0"
    output["flowCode"] = "M"
    output["flowDesc"] = "Import"

    columns = [
        "period", "reporterCode", "reporterISO", "reporterDesc", "flowCode", "flowDesc",
        "partnerCode", "partnerISO", "partnerDesc", "cmdCode", "cmdDesc", "primaryValue",
    ]
    return output[columns]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sheet")
    args = parser.parse_args()

    normalized = normalize(load_table(args.input, args.sheet))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Normalized {len(normalized):,} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
