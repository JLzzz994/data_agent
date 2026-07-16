from typing import Annotated, TypedDict, Any

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class ColumnInfoState(TypedDict):
    name: str
    type: str
    role: str
    example: list[Any]
    description: str
    alias: list[str]


class TableInfoState(TypedDict):
    name: str
    role: str
    description: str
    columns: list[ColumnInfoState]


class MetricInfoState(TypedDict):
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


class DateInfoState(TypedDict):
    date: str  # 日期
    weekday: str  # 星期
    quarter: str  # 季度


class DBInfoState(TypedDict):
    dialect: str  # 数据库方言
    version: str  # 数据库版本


class DataAgentState(TypedDict):
    query: str
    keywords: str

    recall_values: list[ValueInfo]
    recall_metrics: list[MetricInfo]
    recall_columns: list[ColumnInfo]

    table_infos: list[TableInfoState]  # 合并后的表信息
    metric_infos: list[MetricInfoState]  # 合并后的指标信息

    date_info: DateInfoState  # 当前的日期信息
    db_info: DBInfoState  # 数据库信息

    sql: str  # 生成的SQL语句
    error: str  # 校验sql产生的错误信息
