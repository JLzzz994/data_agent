import tempfile
import unittest
from collections import Counter
from pathlib import Path

from app.security.scoped_sql import TABLE_ACCESS_POLICY
from app.security.sql_guard import validate_readonly_sql
from evaluation.build_fixed_500 import expand_spec, write_jsonl
from evaluation.core import load_cases

ROOT = Path(__file__).parents[1]
SPEC = ROOT / "evaluation" / "fixed_500.spec.json"
DATASET = ROOT / "evaluation" / "fixed_500.jsonl"


class Fixed500DatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = expand_spec(SPEC)
        cls.cases = load_cases(DATASET)

    def test_exactly_500_fixed_cases(self):
        self.assertEqual(500, len(self.rows))
        self.assertEqual(500, len(self.cases))
        self.assertEqual(500, len({case.id for case in self.cases}))
        self.assertEqual(500, len({case.question for case in self.cases}))

    def test_50_semantics_each_have_10_paraphrases(self):
        counts = Counter(case.semantic_id for case in self.cases)
        self.assertEqual(50, len(counts))
        self.assertEqual({10}, set(counts.values()))
        self.assertEqual(50, len({case.gold_sql for case in self.cases}))

    def test_committed_jsonl_matches_deterministic_builder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "fixed_500.jsonl"
            write_jsonl(self.rows, output)
            self.assertEqual(
                DATASET.read_text(encoding="utf-8"),
                output.read_text(encoding="utf-8"),
            )

    def test_gold_sql_is_readonly_and_uses_protected_tables(self):
        for case in self.cases:
            validate_readonly_sql(case.gold_sql)
            self.assertTrue(case.expected_tables)
            for table in case.expected_tables:
                self.assertIn(table, TABLE_ACCESS_POLICY, case.id)

    def test_questions_use_fixed_dates_not_moving_relative_time(self):
        forbidden = ("最近", "本月", "上月", "今天", "昨天", "当前")
        for case in self.cases:
            self.assertFalse(
                any(word in case.question for word in forbidden),
                case.question,
            )

    def test_business_categories_and_difficulties_are_covered(self):
        categories = {case.category for case in self.cases}
        difficulties = {case.difficulty for case in self.cases}
        self.assertTrue(
            {"sales", "profitability", "inventory", "purchase", "after_sale"}
            .issubset(categories)
        )
        self.assertTrue({"easy", "medium", "hard"}.issubset(difficulties))


if __name__ == "__main__":
    unittest.main()
