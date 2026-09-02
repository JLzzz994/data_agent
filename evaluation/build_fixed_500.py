"""从固定 spec 可重复生成 500 条 Text2SQL JSONL。"""
import argparse
import json
from pathlib import Path


def expand_spec(spec_path: Path) -> list[dict]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    templates = spec["question_templates"]
    scope = spec["default_scope"]
    rows = []
    counter = 1
    for item in spec["cases"]:
        for template in templates:
            rows.append({
                "id": f"hj-eval-{counter:04d}",
                "dataset_version": spec["version"],
                "semantic_id": item["semantic_id"],
                "question": template.format(core=item["core"]),
                "gold_sql": item["gold_sql"],
                "category": item["category"],
                "difficulty": item["difficulty"],
                "expected_tables": item["expected_tables"],
                "expected_metrics": item.get("expected_metrics", []),
                "tags": item.get("tags", []),
                "tenant_id": scope["tenant_id"],
                "shop_ids": scope["shop_ids"],
                "order_sensitive": spec.get("order_sensitive", False),
            })
            counter += 1
    return rows


def write_jsonl(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).with_name("fixed_500.spec.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("fixed_500.jsonl"),
    )
    args = parser.parse_args()
    rows = expand_spec(args.spec)
    if len(rows) != 500:
        raise SystemExit(f"固定评测集必须为 500 条，实际 {len(rows)} 条")
    write_jsonl(rows, args.output)
    print(f"wrote {len(rows)} cases to {args.output}")


if __name__ == "__main__":
    main()
