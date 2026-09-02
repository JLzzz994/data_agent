import unittest

from app.security.sql_guard import validate_readonly_sql


class SQLGuardTest(unittest.TestCase):
    def test_readonly_sql_passes(self):
        valid_sql = [
            "SELECT shop_id, SUM(paid_amount) FROM fact_trade_order GROUP BY shop_id",
            "WITH t AS (SELECT * FROM fact_trade_order) SELECT COUNT(*) FROM t",
        ]
        for sql in valid_sql:
            validate_readonly_sql(sql)

    def test_non_readonly_sql_is_rejected(self):
        invalid_sql = [
            "DELETE FROM fact_trade_order",
            "UPDATE fact_trade_order SET paid_amount = 0",
            "SELECT * FROM fact_trade_order; DROP TABLE fact_trade_order",
            "CREATE TABLE hacked(id INT)",
            "SET @x = 1",
        ]
        for sql in invalid_sql:
            with self.assertRaises(ValueError):
                validate_readonly_sql(sql)


if __name__ == "__main__":
    unittest.main()
