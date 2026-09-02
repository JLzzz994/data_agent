from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.sql_guard import validate_readonly_sql


class DWMSQLRepository:
    """慧经营只读数据仓库持久层。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name) -> dict[str, str]:
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.all()}

    async def get_column_values(self, table_name, column_name, limit: int = 10) -> list:
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return result.scalars().all()

    async def get_db_info(self):
        name = self.session.get_bind().dialect.name
        result = await self.session.execute(text("select version()"))
        return {"dialect": name, "version": result.scalar()}

    async def validate_sql(self, sql: str, timeout_ms: int = 10_000):
        dialect = self.session.get_bind().dialect.name or "mysql"
        validate_readonly_sql(sql, dialect=dialect)
        if dialect == "mysql":
            await self.session.execute(text(f"SET SESSION MAX_EXECUTION_TIME = {int(timeout_ms)}"))
        await self.session.execute(text(f"EXPLAIN {sql}"))

    async def execute_sql(self, sql: str, max_rows: int = 500, timeout_ms: int = 10_000):
        dialect = self.session.get_bind().dialect.name or "mysql"
        validate_readonly_sql(sql, dialect=dialect)
        if dialect == "mysql":
            await self.session.execute(text(f"SET SESSION MAX_EXECUTION_TIME = {int(timeout_ms)}"))
        result = await self.session.execute(text(sql))
        rows = result.mappings().fetchmany(size=max_rows)
        return [dict(mapping) for mapping in rows]
