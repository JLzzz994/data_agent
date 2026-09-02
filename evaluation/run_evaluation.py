"""运行固定 Text2SQL 评测，按 gold SQL 执行结果等价计算准确率。"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.security.access_scope import AccessScope
from app.security.result_masking import mask_rows
from app.security.scoped_sql import apply_access_scope
from evaluation.core import (
    EvaluationCase,
    classify_failure,
    compare_rows,
    extract_trace,
    load_cases,
)


def _post_sse(
    api_url: str,
    case: EvaluationCase,
    gateway_token: str,
    timeout_seconds: float,
) -> list[dict]:
    body = json.dumps({"query": case.question, "max_rows": 1000}).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Internal-Tenant-Id": case.tenant_id,
            "X-Internal-Shop-Ids": ",".join(case.shop_ids),
            "X-Internal-Gateway-Token": gateway_token,
        },
    )
    events: list[dict] = []
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload = line.removeprefix("data:").strip()
            if payload:
                events.append(json.loads(payload))
    return events


def _result_rows(events: list[dict]) -> list[dict] | None:
    for event in reversed(events):
        if event.get("type") == "result" and "data" in event:
            return event["data"]
    return None


async def build_gold_cache(cases: list[EvaluationCase]) -> dict[tuple, list[dict]]:
    cache: dict[tuple, list[dict]] = {}
    dw_mysql_client_manager.init()
    try:
        for case in cases:
            key = (case.gold_sql, case.tenant_id, case.shop_ids)
            if key in cache:
                continue
            scope = AccessScope(case.tenant_id, case.shop_ids)
            secured_sql = apply_access_scope(case.gold_sql, scope)
            async with dw_mysql_client_manager.session_factory() as session:
                repository = DWMSQLRepository(session)
                rows = await repository.execute_sql(secured_sql, max_rows=1000)
                cache[key] = mask_rows(rows)
    finally:
        await dw_mysql_client_manager.close()
    return cache


async def evaluate_case(
    case: EvaluationCase,
    api_url: str,
    gateway_token: str,
    timeout_seconds: float,
    semaphore: asyncio.Semaphore,
    gold_cache: dict[tuple, list[dict]],
) -> dict[str, Any]:
    started = time.perf_counter()
    events: list[dict] = []
    request_error = None
    async with semaphore:
        try:
            events = await asyncio.to_thread(
                _post_sse,
                api_url,
                case,
                gateway_token,
                timeout_seconds,
            )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            request_error = str(exc)

    predicted = _result_rows(events)
    gold = gold_cache[(case.gold_sql, case.tenant_id, case.shop_ids)]
    passed = False
    reason = None
    if request_error is None and predicted is not None:
        passed, reason = compare_rows(
            predicted,
            gold,
            order_sensitive=case.order_sensitive,
        )
    elif request_error is None:
        reason = "missing_result"

    trace = extract_trace(events)
    failure_type = "pass" if passed else classify_failure(
        case,
        events,
        reason,
        request_error=request_error,
    )
    return {
        "id": case.id,
        "semantic_id": case.semantic_id,
        "question": case.question,
        "category": case.category,
        "difficulty": case.difficulty,
        "passed": passed,
        "failure_type": failure_type,
        "reason": request_error or reason,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "predicted_rows": None if predicted is None else len(predicted),
        "gold_rows": len(gold),
        "generated_sql": trace.get("generated_sql"),
        "final_sql": trace.get("final_sql"),
        "correction_rounds": len(trace.get("corrections", [])),
        "selected_tables": trace.get("selected_tables", []),
        "selected_metrics": trace.get("selected_metrics", []),
        "events": events,
    }


def _group_accuracy(rows: list[dict], field: str) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {
        name: {
            "total": len(items),
            "passed": sum(1 for item in items if item["passed"]),
            "accuracy": round(
                sum(1 for item in items if item["passed"]) / len(items),
                4,
            ),
        }
        for name, items in sorted(groups.items())
    }


def build_summary(
    rows: list[dict],
    target_accuracy: float,
    dataset_path: Path,
) -> dict:
    passed = sum(1 for row in rows if row["passed"])
    total = len(rows)
    accuracy = passed / total if total else 0.0
    return {
        "dataset": str(dataset_path),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "execution_accuracy": round(accuracy, 4),
        "target_accuracy": target_accuracy,
        "target_met": accuracy >= target_accuracy,
        "target_gap": round(accuracy - target_accuracy, 4),
        "average_latency_ms": round(
            sum(row["latency_ms"] for row in rows) / total,
            2,
        ) if total else 0,
        "failure_counts": dict(Counter(
            row["failure_type"] for row in rows if not row["passed"]
        )),
        "by_category": _group_accuracy(rows, "category"),
        "by_difficulty": _group_accuracy(rows, "difficulty"),
        "correction_rounds": dict(Counter(
            str(row["correction_rounds"]) for row in rows
        )),
    }


def write_reports(rows: list[dict], summary: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation.json").write_text(
        json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_fields = [
        "id", "semantic_id", "category", "difficulty", "passed",
        "failure_type", "reason", "latency_ms", "predicted_rows", "gold_rows",
        "correction_rounds", "generated_sql", "final_sql", "question",
    ]
    with (output_dir / "evaluation.csv").open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in csv_fields})

    markdown = [
        "# 慧经营 Text2SQL 评测报告",
        "",
        f"- 样本数：**{summary['total']}**",
        f"- 执行正确：**{summary['passed']}**",
        f"- 执行准确率：**{summary['execution_accuracy']:.2%}**",
        f"- 目标准确率：**{summary['target_accuracy']:.2%}**",
        f"- 是否达到目标：**{'是' if summary['target_met'] else '否'}**",
        f"- 平均延迟：**{summary['average_latency_ms']} ms**",
        "",
        "## Bad case 分类",
        "",
        "| 类型 | 数量 |",
        "|---|---:|",
    ]
    for failure_type, count in sorted(
        summary["failure_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        markdown.append(f"| {failure_type} | {count} |")

    markdown.extend([
        "",
        "## 按业务分类",
        "",
        "| 分类 | 通过/总数 | 准确率 |",
        "|---|---:|---:|",
    ])
    for name, item in summary["by_category"].items():
        markdown.append(
            f"| {name} | {item['passed']}/{item['total']} | {item['accuracy']:.2%} |"
        )

    markdown.extend([
        "",
        "## 按难度",
        "",
        "| 难度 | 通过/总数 | 准确率 |",
        "|---|---:|---:|",
    ])
    for name, item in summary["by_difficulty"].items():
        markdown.append(
            f"| {name} | {item['passed']}/{item['total']} | {item['accuracy']:.2%} |"
        )

    failed = [row for row in rows if not row["passed"]]
    markdown.extend([
        "",
        "## 前 30 个 Bad Cases",
        "",
        "| ID | 类型 | 问题 | 原因 |",
        "|---|---|---|---|",
    ])
    for row in failed[:30]:
        question = row["question"].replace("|", "\\|")
        reason = str(row.get("reason") or "").replace("|", "\\|")
        markdown.append(
            f"| {row['id']} | {row['failure_type']} | {question} | {reason} |"
        )

    (output_dir / "evaluation.md").write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )


async def async_main(args) -> int:
    cases = load_cases(args.dataset)
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        raise SystemExit("没有可评测样本")

    gateway_token = args.gateway_token or os.getenv("INTERNAL_GATEWAY_TOKEN", "")
    if not gateway_token:
        raise SystemExit("请通过 --gateway-token 或 INTERNAL_GATEWAY_TOKEN 提供内部网关凭证")

    print(f"preflight: executing {len({case.gold_sql for case in cases})} unique gold SQLs")
    gold_cache = await build_gold_cache(cases)
    semaphore = asyncio.Semaphore(args.workers)
    rows = await asyncio.gather(*[
        evaluate_case(
            case,
            args.api_url,
            gateway_token,
            args.timeout,
            semaphore,
            gold_cache,
        )
        for case in cases
    ])
    summary = build_summary(rows, args.target_accuracy, args.dataset)
    write_reports(rows, summary, args.output_dir)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.enforce_target and not summary["target_met"]:
        return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).with_name("fixed_500.jsonl"),
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000/api/query",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/evaluation"),
    )
    parser.add_argument("--gateway-token", default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--target-accuracy", type=float, default=0.88)
    parser.add_argument("--enforce-target", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()
