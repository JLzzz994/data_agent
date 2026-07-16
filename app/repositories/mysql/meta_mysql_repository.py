from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.entities.column_info import ColumnInfo
from app.mappers.column_info_mapper import ColumnInfoMapper
from app.mappers.table_info_mapper import TableInfoMapper
from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL


class MetaMySQLRepository:
    '''
    操作元数据库 表 字段 指标 字段指标 持久层
    '''

    def __init__(self, session: AsyncSession):
        self.session = session

    def save_table_infos(self, table_infos: list[TableInfoMySQL]):
        self.session.add_all(table_infos)

    def save_column_infos(self, column_infos: list[ColumnInfoMySQL]):
        self.session.add_all(column_infos)

    def save_metric_infos(self, metric_infos: list[MetricInfoMySQL]):
        self.session.add_all(metric_infos)

    def save_column_metrics(self, column_metrics: list[ColumnMetricMySQL]):
        self.session.add_all(column_metrics)

    async def get_column_info_by_id(self, column_id: str) -> ColumnInfo:
        '''根据字段id 查询字段'''
        column_info_mysql: ColumnInfoMySQL = await self.session.get(ColumnInfoMySQL, column_id)
        return ColumnInfoMapper.to_entity(column_info_mysql)

    async def get_table_by_id(self, table_id: str):
        '''
        根据table_id 查表信息
        :param table_id:
        :return:
        '''
        table_info_mysql: TableInfoMySQL = await self.session.get(TableInfoMySQL, table_id)
        return TableInfoMapper.to_entity(table_info_mysql)

    async def get_columns_by_ids(self, column_ids: list[str]):
        '''
        根据 column_id 列表批量查询字段信息
        :param column_ids:
        :return:
        '''
        if not column_ids:
            return []

        # 使用 in_ 查询批量获取
        stmt = select(ColumnInfoMySQL).where(ColumnInfoMySQL.id.in_(column_ids))
        result = await self.session.execute(stmt)
        column_infos_mysql = result.scalars().all()

        return [ColumnInfoMapper.to_entity(column_info_mysql) for column_info_mysql in column_infos_mysql]

    async def get_key_columns_by_table_id(self, table_id: str):
        '''
        根据 table_id 查询主外键
        :param table_id:
        :return:
        '''

        stmt = select(ColumnInfoMySQL).where(
            ColumnInfoMySQL.table_id == table_id,
            ColumnInfoMySQL.role.in_(["primary_key", "foreign_key"])
        )
        result = await self.session.scalars(stmt)

        return [ColumnInfoMapper.to_entity(key_column_info_mysql) for key_column_info_mysql in result]


if __name__ == '__main__':
    async def test_key_columns():
        meta_mysql_client_manager.init()
        assert meta_mysql_client_manager.session_factory
        async with meta_mysql_client_manager.session_factory() as session:
            result = await MetaMySQLRepository(session).get_key_columns_by_table_id("fact_order")
            print(result)
    # asyncio.run(test_key_columns())
