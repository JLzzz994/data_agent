from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMSQLRepository:
    '''
    操作数据仓库dw库 持久层
    '''

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name) -> dict[str, str]:
        '''
        查询dw库中指定表的字段类型
        :param table_name: str
        :return: dict[str,str]
        '''

        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.all()}

    async def get_column_values(self, table_name, column_name, limit: int = 10) -> list:
        '''
        查询dw库指定字段的10条数据
        :param table_name:
        :param column_name:
        :param limit:
        :return:
        '''
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return result.scalars().all()

    async def get_db_info(self):
        name = self.session.get_bind().dialect.name
        sql = "select version()"
        result = await self.session.execute(text(sql))
        return {"dialect": name, "version": result.scalar()}

    async def validate_sql(self, sql:str):
        await self.session.execute(text(f"explain {sql}"))

    async def execute_sql(self, sql:str):
        result = await self.session.execute(text(sql))
        return [dict(mapping) for mapping in result.mappings().all()]