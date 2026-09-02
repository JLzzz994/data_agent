import unittest

from app.security.access_scope import AccessScope
from app.security.scoped_sql import apply_access_scope


class ScopedSQLTest(unittest.TestCase):
    def setUp(self):
        self.scope = AccessScope(
            tenant_id="tenant_hc_001",
            allowed_shop_ids=("shop_tmall_001", "shop_jd_001"),
        )

    def test_trade_order_is_wrapped_with_tenant_and_shop_scope(self):
        sql = "SELECT shop_id, SUM(paid_amount) FROM fact_trade_order GROUP BY shop_id"
        secured = apply_access_scope(sql, self.scope)
        self.assertIn("tenant_hc_001", secured)
        self.assertIn("shop_tmall_001", secured)
        self.assertIn("shop_jd_001", secured)
        self.assertIn("fact_trade_order", secured)

    def test_cte_reference_is_not_mistaken_for_physical_table(self):
        sql = (
            "WITH recent AS (SELECT * FROM fact_trade_order) "
            "SELECT COUNT(*) FROM recent"
        )
        secured = apply_access_scope(sql, self.scope)
        self.assertIn("tenant_hc_001", secured)
        self.assertIn("FROM recent", secured)

    def test_cte_cannot_shadow_protected_table_name(self):
        sql = (
            "WITH fact_trade_order AS (SELECT 1 AS x) "
            "SELECT * FROM fact_trade_order"
        )
        with self.assertRaises(PermissionError):
            apply_access_scope(sql, self.scope)

    def test_table_policy_is_case_insensitive(self):
        secured = apply_access_scope(
            "SELECT * FROM FACT_TRADE_ORDER",
            self.scope,
        )
        self.assertIn("tenant_hc_001", secured)

    def test_unknown_table_is_rejected(self):
        with self.assertRaises(PermissionError):
            apply_access_scope("SELECT * FROM secret_table", self.scope)

    def test_shop_scoped_table_requires_shop_permissions(self):
        no_shop_scope = AccessScope(tenant_id="tenant_hc_001")
        with self.assertRaises(PermissionError):
            apply_access_scope("SELECT * FROM fact_trade_order", no_shop_scope)

    def test_tenant_only_dimension_does_not_require_shop_scope(self):
        no_shop_scope = AccessScope(tenant_id="tenant_hc_001")
        secured = apply_access_scope("SELECT * FROM dim_goods", no_shop_scope)
        self.assertIn("tenant_hc_001", secured)


if __name__ == "__main__":
    unittest.main()
