import unittest
from decimal import Decimal

from evaluation.core import (
    EvaluationCase,
    classify_failure,
    compare_rows,
    extract_trace,
)


class EvaluationCoreTest(unittest.TestCase):
    def test_numeric_json_strings_equal_database_decimals(self):
        predicted = [{"shop_name": "华策旗舰店", "paid_sales": "1354.00"}]
        gold = [{"shop_name": "华策旗舰店", "paid_sales": Decimal("1354.000")}]
        passed, reason = compare_rows(predicted, gold)
        self.assertTrue(passed)
        self.assertIsNone(reason)

    def test_alias_names_do_not_change_execution_accuracy(self):
        predicted = [{"sales": "1354.00"}]
        gold = [{"paid_sales": Decimal("1354.00")}]
        passed, reason = compare_rows(predicted, gold)
        self.assertTrue(passed)
        self.assertIsNone(reason)

    def test_row_order_is_ignored_by_default(self):
        predicted = [{"x": 2}, {"x": 1}]
        gold = [{"x": 1}, {"x": 2}]
        passed, _ = compare_rows(predicted, gold, order_sensitive=False)
        self.assertTrue(passed)

    def test_column_count_mismatch_is_classified(self):
        passed, reason = compare_rows([{"a": 1}], [{"a": 1, "b": 2}])
        self.assertFalse(passed)
        self.assertTrue(reason.startswith("column_mismatch"))

    def test_row_count_mismatch_is_classified(self):
        passed, reason = compare_rows([{"x": 1}], [{"x": 1}, {"x": 2}])
        self.assertFalse(passed)
        self.assertTrue(reason.startswith("row_count_mismatch"))

    def test_trace_extracts_sql_tables_metrics_and_corrections(self):
        events = [
            {"type": "eval_trace", "stage": "filtered_tables", "tables": ["fact_trade_order"]},
            {"type": "eval_trace", "stage": "filtered_metrics", "metrics": ["paid_sales"]},
            {"type": "eval_trace", "stage": "generated_sql", "sql": "SELECT 1"},
            {"type": "eval_trace", "stage": "corrected_sql", "round": 1, "sql": "SELECT 2"},
        ]
        trace = extract_trace(events)
        self.assertEqual(["fact_trade_order"], trace["selected_tables"])
        self.assertEqual(["paid_sales"], trace["selected_metrics"])
        self.assertEqual("SELECT 2", trace["final_sql"])
        self.assertEqual(1, len(trace["corrections"]))

    def test_missing_expected_table_becomes_schema_linking_miss(self):
        case = EvaluationCase(
            id="x",
            dataset_version="v1",
            semantic_id="s1",
            question="q",
            gold_sql="SELECT 1",
            category="sales",
            difficulty="easy",
            expected_tables=("fact_trade_order", "dim_shop"),
            expected_metrics=(),
            tags=(),
            tenant_id="tenant_hc_001",
            shop_ids=("shop_tmall_001",),
        )
        events = [{
            "type": "eval_trace",
            "stage": "filtered_tables",
            "tables": ["fact_trade_order"],
        }]
        self.assertEqual(
            "schema_linking_miss",
            classify_failure(case, events, "value_mismatch"),
        )

    def test_semantic_rejection_has_specific_bad_case_type(self):
        case = EvaluationCase(
            id="x",
            dataset_version="v1",
            semantic_id="s1",
            question="q",
            gold_sql="SELECT 1",
            category="sales",
            difficulty="easy",
            expected_tables=(),
            expected_metrics=(),
            tags=(),
            tenant_id="tenant_hc_001",
            shop_ids=(),
        )
        events = [{
            "type": "progress",
            "step": "校验sql",
            "status": "error",
            "message": "语义一致性校验失败: 时间范围错误",
        }]
        self.assertEqual(
            "semantic_validation_rejected",
            classify_failure(case, events, None),
        )


if __name__ == "__main__":
    unittest.main()
