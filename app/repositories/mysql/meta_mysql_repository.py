from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL


class MetaMySQLRepository:
    '''
    操作元数据库 表 字段 指标 字段指标 持久层
    '''
    def __init__(self,session:AsyncSession):
        self.session = session

    def save_table_infos(self, table_infos:list[TableInfoMySQL]):
        self.session.add_all(table_infos)

    def save_column_infos(self, column_infos:list[ColumnInfoMySQL]):
        self.session.add_all(column_infos)

    def save_metric_infos(self, metric_infos:list[MetricInfoMySQL]):
        self.session.add_all(metric_infos)

    def save_column_metrics(self, column_metrics:list[ColumnMetricMySQL]):
        self.session.add_all(column_metrics)