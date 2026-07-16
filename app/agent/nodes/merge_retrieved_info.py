"""合并召回信息节点。

将字段、指标、取值等多路召回结果合并为统一上下文。
"""
from dataclasses import asdict

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, TableInfoState, MetricInfoState, ColumnInfoState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """合并多路召回结果。"""
    # 合并字段/指标/取值信息，
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "合并结果", "status": "running"})
    try:
        logger.info("开始合并结果")
        # 3. 业务逻辑
        recall_columns: list[ColumnInfo] = state["recall_columns"]
        recall_metrics: list[MetricInfo] = state["recall_metrics"]
        recall_values: list[ValueInfo] = state["recall_values"]
        meta_mysql_repository = runtime.context["meta_mysql_repository"]

        table_infos: list[TableInfoState] = []
        # 对于指标计算:后续可能存在公式和例子
        metric_infos: list[MetricInfoState] = []

        # 3.1 遍历指标的相关字段 补充id_to_column_map中没有的字段信息
        id_to_column_map: dict[str, ColumnInfo] = {item.id: item for item in recall_columns}
        for recall_metric in recall_metrics:
            relevant_columns = recall_metric.relevant_columns
            # 如果这个相关字段的column_id不在,那么查询column_id的字段信息 补充到id_to_column_map中
            for column_id in relevant_columns:
                if column_id not in id_to_column_map:
                    column_info: ColumnInfo = await meta_mysql_repository.get_column_info_by_id(column_id)
                    id_to_column_map[column_id] = column_info

        # 3.2 遍历字段取值  补充id_to_column_map中没有的字段信息和examples
        for recall_value in recall_values:
            column_id = recall_value.column_id
            value = recall_value.value
            # 如果这个字段值所属的column_id 不在id_to_column_map
            if column_id not in id_to_column_map:
                # 查询column_id对应的字段信息 补充到id_to_column_map中
                column_info: ColumnInfo = await meta_mysql_repository.get_column_info_by_id(column_id)
                id_to_column_map[column_id] = column_info
            # examples中如果没有这个值 补充进去
            if value not in id_to_column_map[column_id].examples:
                id_to_column_map[column_id].examples.append(value)

        # 3.3 字段字典 转为table_to_columns_map {表id :字段列表} ColumnInfo:dataclass
        #  根据 table_id 分组
        table_to_columns_map: dict[str, list[ColumnInfo]] = {}
        # 遍历id_to_column_map
        for column_info in id_to_column_map.values():
            table_id = column_info.table_id
            if table_id not in table_to_columns_map:
                table_to_columns_map[table_id] = []
            table_to_columns_map[table_id].append(column_info)

        # 3.4 分组后,转为table_info_state ,查询表信息 补充到table_info_state中
        for table_id, columns in table_to_columns_map.items():
            table_info: TableInfo = await meta_mysql_repository.get_table_by_id(table_id)
            # 把columns转为column_info_state
            column_state_ids: list[str] = [column.id for column in columns]
            column_states: list[ColumnInfoState] = [ColumnInfoState(**asdict(column)) for column in columns]

            # 3.5  添加主外键信息
            key_columns: list[ColumnInfo] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)
            column_states.extend(ColumnInfoState(**asdict(key_column)) for key_column in key_columns if
                                  key_column.id not in column_state_ids)
            table_info_state = TableInfoState(
                name=table_info.name,
                role=table_info.role,
                description=table_info.description,
                columns=column_states
            )
            table_infos.append(table_info_state)

        # 4. 遍历指标
        for recall_metric in recall_metrics:
            metric_infos.append(MetricInfoState(
                name=recall_metric.name,
                description=recall_metric.description,
                relevant_columns=recall_metric.relevant_columns,
                alias=recall_metric.alias
            ))

        # 5. 业务正常 成功
        writer({"type": "progress", "step": "合并结果", "status": "success"})

        logger.info(
            f"合并结果成功表信息:{[table_info['name'] for table_info in table_infos]},指标信息:{[metric_info['name'] for metric_info in metric_infos]}")
        return {"table_infos": table_infos, "metric_infos": metric_infos}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "合并结果", "status": "error"})
        logger.error(f"合并结果失败{e}")
        raise
