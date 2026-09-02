from typing import Any, TypedDict

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
    date: str
    time: str
    weekday: str
    quarter: str
    timezone: str


class DBInfoState(TypedDict):
    dialect: str
    version: str


class DataAgentState(TypedDict, total=False):
    query: str
    keywords: str
    recall_values: list[ValueInfo]
    recall_metrics: list[MetricInfo]
    recall_columns: list[ColumnInfo]
    table_infos: list[TableInfoState]
    metric_infos: list[MetricInfoState]
    date_info: DateInfoState
    db_info: DBInfoState
    sql: str
    error: str | None
    retry_count: int
    max_rows: int
    validation_stage: str | None
    semantic_validation: str | None
