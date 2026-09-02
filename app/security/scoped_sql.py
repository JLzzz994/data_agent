"""把租户/店铺数据权限确定性注入 SQL，不依赖 LLM。"""
from sqlglot import exp, parse_one

from app.security.access_scope import AccessScope

# True 表示除 tenant_id 外还必须限制 shop_id。
TABLE_ACCESS_POLICY: dict[str, bool] = {
    "dim_shop": True,
    "dim_goods": False,
    "dim_warehouse": False,
    "fact_trade_order": True,
    "fact_inventory_snapshot": True,
    "fact_purchase": True,
    "fact_after_sale": True,
}


def _quote(value: str) -> str:
    return value.replace("'", "''")


def apply_access_scope(sql: str, scope: AccessScope, dialect: str = "mysql") -> str:
    statement = parse_one(sql, read=dialect)
    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}

    # 不允许 CTE 冒用受控物理表名，避免物理表与逻辑别名产生权限歧义。
    conflicts = cte_names.intersection(TABLE_ACCESS_POLICY)
    if conflicts:
        raise PermissionError(
            f"CTE 名称与受控物理表冲突: {', '.join(sorted(conflicts))}"
        )

    # 冻结原始 Table 列表，避免继续处理新插入的安全子查询内部表。
    tables = list(statement.find_all(exp.Table))
    for table in tables:
        table_name = table.name.lower()
        if table_name in cte_names:
            continue
        if table_name not in TABLE_ACCESS_POLICY:
            raise PermissionError(f"表 {table.name} 未配置租户数据权限策略")

        base_table = table.copy()
        base_table.set("alias", None)

        predicates = [f"tenant_id = '{_quote(scope.tenant_id)}'"]
        if TABLE_ACCESS_POLICY[table_name]:
            if not scope.allowed_shop_ids:
                raise PermissionError(f"当前身份没有 {table.name} 的店铺访问范围")
            shops = ", ".join(
                f"'{_quote(shop_id)}'" for shop_id in scope.allowed_shop_ids
            )
            predicates.append(f"shop_id IN ({shops})")

        secured_select = (
            exp.select("*")
            .from_(base_table)
            .where(parse_one(" AND ".join(predicates), read=dialect))
        )
        table.replace(secured_select.subquery(alias=table.alias_or_name))

    return statement.sql(dialect=dialect)
