"""Text2SQL 执行结果比较与 bad case 分类。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    dataset_version: str
    semantic_id: str
    question: str
    gold_sql: str
    category: str
    difficulty: str
    expected_tables: tuple[str, ...]
    expected_metrics: tuple[str, ...]
    tags: tuple[str, ...]
    tenant_id: str
    shop_ids: tuple[str, ...]
    order_sensitive: bool = False


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            try:
                cases.append(EvaluationCase(
                    id=raw["id"],
                    dataset_version=raw["dataset_version"],
                    semantic_id=raw["semantic_id"],
                    question=raw["question"],
                    gold_sql=raw["gold_sql"],
                    category=raw["category"],
                    difficulty=raw["difficulty"],
                    expected_tables=tuple(raw.get("expected_tables", [])),
                    expected_metrics=tuple(raw.get("expected_metrics", [])),
                    tags=tuple(raw.get("tags", [])),
                    tenant_id=raw["tenant_id"],
                    shop_ids=tuple(raw.get("shop_ids", [])),
                    order_sensitive=bool(raw.get("order_sensitive", False)),
                ))
            except KeyError as exc:
                raise ValueError(f"{path}:{line_number} 缺少字段 {exc}") from exc
    return cases


def _normalize_decimal(value: Any) -> str:
    decimal_value = Decimal(str(value))
    if decimal_value == 0:
        return "0"
    normalized = decimal_value.normalize()
    return format(normalized, "f")


def normalize_scalar(value: Any):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return ("number", _normalize_decimal(value))
    if isinstance(value, (datetime, date)):
        return ("time", value.isoformat())
    if isinstance(value, str):
        stripped = value.strip()
        if _NUMBER_RE.fullmatch(stripped):
            try:
                return ("number", _normalize_decimal(stripped))
            except InvalidOperation:
                pass
        return ("text", stripped)
    return ("text", str(value))


def canonicalize_rows(rows: list[dict], order_sensitive: bool = False) -> list[tuple]:
    # execution accuracy 比较列位置和值，不要求 SQL 别名与 gold 完全一致。
    canonical = [
        tuple(normalize_scalar(value) for value in row.values())
        for row in rows
    ]
    if not order_sensitive:
        canonical.sort(key=repr)
    return canonical


def compare_rows(
    predicted: list[dict],
    gold: list[dict],
    order_sensitive: bool = False,
) -> tuple[bool, str | None]:
    if len(predicted) != len(gold):
        return False, f"row_count_mismatch: predicted={len(predicted)}, gold={len(gold)}"

    predicted_widths = {len(row) for row in predicted}
    gold_widths = {len(row) for row in gold}
    if predicted_widths != gold_widths:
        return False, (
            "column_mismatch: "
            f"predicted_widths={sorted(predicted_widths)}, "
            f"gold_widths={sorted(gold_widths)}"
        )

    predicted_rows = canonicalize_rows(predicted, order_sensitive)
    gold_rows = canonicalize_rows(gold, order_sensitive)
    if predicted_rows != gold_rows:
        for index, (predicted_row, gold_row) in enumerate(
            zip(predicted_rows, gold_rows),
            start=1,
        ):
            if predicted_row != gold_row:
                return False, (
                    f"value_mismatch: row={index}, "
                    f"predicted={predicted_row}, gold={gold_row}"
                )
        return False, "value_mismatch"
    return True, None


def extract_trace(events: list[dict]) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "generated_sql": None,
        "corrections": [],
        "selected_tables": [],
        "selected_metrics": [],
        "has_filtered_tables": False,
        "has_filtered_metrics": False,
    }
    for event in events:
        if event.get("type") != "eval_trace":
            continue
        stage = event.get("stage")
        if stage == "filtered_tables":
            trace["has_filtered_tables"] = True
            trace["selected_tables"] = event.get("tables", [])
        elif stage == "filtered_metrics":
            trace["has_filtered_metrics"] = True
            trace["selected_metrics"] = event.get("metrics", [])
        elif stage == "generated_sql":
            trace["generated_sql"] = event.get("sql")
        elif stage == "corrected_sql":
            trace["corrections"].append({
                "round": event.get("round"),
                "sql": event.get("sql"),
            })
    if trace["corrections"]:
        trace["final_sql"] = trace["corrections"][-1]["sql"]
    else:
        trace["final_sql"] = trace["generated_sql"]
    return trace


def classify_failure(
    case: EvaluationCase,
    events: list[dict],
    comparison_reason: str | None,
    request_error: str | None = None,
) -> str:
    if request_error:
        if "timed out" in request_error.lower() or "timeout" in request_error.lower():
            return "transport_timeout"
        return "transport_error"

    trace = extract_trace(events)
    selected_tables = set(trace.get("selected_tables") or [])
    selected_metrics = set(trace.get("selected_metrics") or [])
    if (
        trace.get("has_filtered_tables")
        and not set(case.expected_tables).issubset(selected_tables)
    ):
        return "schema_linking_miss"
    if (
        case.expected_metrics
        and trace.get("has_filtered_metrics")
        and not set(case.expected_metrics).issubset(selected_metrics)
    ):
        return "metric_recall_miss"

    messages = " ".join(
        str(event.get("message") or event.get("error") or "")
        for event in events
    )
    if "数据权限拒绝" in messages:
        return "access_control_rejected"
    if "语义一致性校验失败" in messages:
        return "semantic_validation_rejected"

    for event in events:
        if event.get("type") != "progress" or event.get("status") != "error":
            continue
        step = event.get("step", "")
        if step in {"召回字段", "召回指标", "召回字段值", "合并结果", "过滤表/字段信息", "过滤指标"}:
            return "retrieval_or_schema_linking_error"
        if step == "生成sql":
            return "sql_generation_error"
        if step == "修正sql":
            return "sql_correction_error"
        if step == "校验sql":
            return "static_explain_or_validation_error"
        if step == "执行sql":
            return "sql_execution_error"

    if comparison_reason:
        return comparison_reason.split(":", 1)[0]
    return "missing_result"
