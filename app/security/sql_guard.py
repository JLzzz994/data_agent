"""确定性 SQL 安全校验。"""
from sqlglot import exp, parse

FORBIDDEN_NODE_TYPES = {
    "ALTER", "COMMAND", "CREATE", "DELETE", "DROP", "GRANT", "INSERT",
    "INTO", "LOCK", "MERGE", "REPLACE", "REVOKE", "SET", "TRANSACTION",
    "TRUNCATETABLE", "UPDATE", "USE",
}


def validate_readonly_sql(sql: str, dialect: str = "mysql") -> None:
    if not sql or not sql.strip():
        raise ValueError("SQL 不能为空")

    statements = [statement for statement in parse(sql, read=dialect) if statement is not None]
    if len(statements) != 1:
        raise ValueError("只允许执行一条 SQL")

    statement = statements[0]
    if statement.find(exp.Select) is None:
        raise ValueError("仅允许 SELECT/CTE 查询")

    for node in statement.walk():
        node_type = type(node).__name__.upper()
        if node_type in FORBIDDEN_NODE_TYPES:
            raise ValueError(f"检测到禁止的 SQL 操作: {node_type}")
