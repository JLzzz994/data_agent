import uuid
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.conf.load_config import load_config
from app.conf.meta_config import MetaConfig, MetricConfig, TableConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo
from app.mappers.column_info_mapper import ColumnInfoMapper
from app.mappers.metric_info_mapper import MetricInfoMapper
from app.models.mysql.column_info_mysql import ColumnInfoMySQL
from app.models.mysql.column_metric_mysql import ColumnMetricMySQL
from app.models.mysql.metric_info_mysql import MetricInfoMySQL
from app.models.mysql.table_info_mysql import TableInfoMySQL
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.milvus.column_milvus_repository import ColumnMilvusRepository
from app.repositories.milvus.metric_milvus_repository import MetricMilvusRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository


class MetaKnowledgeService:
    def __init__(
        self,
        dw_mysql_repository: DWMSQLRepository,
        meta_mysql_repository: MetaMySQLRepository,
        column_milvus_repository: ColumnMilvusRepository,
        embed_client: HuggingFaceEndpointEmbeddings,
        column_value_es_repository: ColumnValueESRepository,
        metric_milvus_repository: MetricMilvusRepository,
    ):
        self.dw_mysql_repository = dw_mysql_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.column_milvus_repository = column_milvus_repository
        self.embed_client = embed_client
        self.column_value_es_repository = column_value_es_repository
        self.metric_milvus_repository = metric_milvus_repository

    async def build(self, config_file: Path):
        meta_config: MetaConfig = load_config(config_file, MetaConfig)

        if meta_config.tables:
            column_infos = await self._save_table_infos_to_meta_db(meta_config.tables)
            logger.info("保存表元数据到 meta 库成功")
            await self._save_column_info_to_milvus(column_infos)
            logger.info("字段语义存入 Milvus 成功")
            await self._save_column_values_to_es(column_infos, meta_config)
            logger.info("字段枚举值存入 Elasticsearch 成功")

        if meta_config.metrics:
            metric_infos = await self._save_metric_infos_to_meta_db(meta_config.metrics)
            logger.info("保存指标元数据到 meta 库成功")
            await self._save_metric_info_to_milvus(metric_infos)
            logger.info("指标语义存入 Milvus 成功")

    async def _save_table_infos_to_meta_db(
        self,
        tables: list[TableConfig],
    ) -> list[ColumnInfo]:
        table_infos: list[TableInfoMySQL] = []
        column_infos: list[ColumnInfoMySQL] = []

        for table in tables:
            table_infos.append(TableInfoMySQL(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            ))
            column_type_dict = await self.dw_mysql_repository.get_column_types(table.name)
            for column in table.columns:
                examples = await self.dw_mysql_repository.get_column_values(
                    table.name,
                    column.name,
                )
                column_infos.append(ColumnInfoMySQL(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_type_dict[column.name],
                    role=column.role,
                    examples=examples,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                ))

        self.meta_mysql_repository.save_table_infos(table_infos)
        self.meta_mysql_repository.save_column_infos(column_infos)
        return [ColumnInfoMapper.to_entity(item) for item in column_infos]

    async def _save_metric_infos_to_meta_db(
        self,
        metrics: list[MetricConfig],
    ) -> list[MetricInfo]:
        metric_infos: list[MetricInfoMySQL] = []
        column_metrics: list[ColumnMetricMySQL] = []

        for metric in metrics:
            metric_infos.append(MetricInfoMySQL(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            ))
            for relevant_column in metric.relevant_columns:
                column_metrics.append(ColumnMetricMySQL(
                    column_id=relevant_column,
                    metric_id=metric.name,
                ))

        self.meta_mysql_repository.save_metric_infos(metric_infos)
        self.meta_mysql_repository.save_column_metrics(column_metrics)
        return [MetricInfoMapper.to_entity(item) for item in metric_infos]

    async def _save_column_info_to_milvus(self, column_infos: list[ColumnInfo]):
        await self.column_milvus_repository.ensure_collection()
        points = []
        for column_info in column_infos:
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": column_info.name,
                "payload": column_info,
            })
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": column_info.description,
                "payload": column_info,
            })
            for alias in column_info.alias:
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": alias,
                    "payload": column_info,
                })

        embeddings: list[list[float]] = []
        texts = [point["embedding_text"] for point in points]
        for i in range(0, len(texts), 20):
            embeddings.extend(
                await self.embed_client.aembed_documents(texts[i:i + 20])
            )

        await self.column_milvus_repository.upsert(
            [point["id"] for point in points],
            embeddings,
            [point["payload"] for point in points],
        )

    async def _save_column_values_to_es(
        self,
        column_infos: list[ColumnInfo],
        meta_config: MetaConfig,
    ):
        await self.column_value_es_repository.ensure_index()
        sync_names = {
            column.name
            for table in meta_config.tables
            for column in table.columns
            if column.sync
        }

        value_infos = []
        for column_info in column_infos:
            if column_info.name not in sync_names:
                continue
            values = await self.dw_mysql_repository.get_column_values(
                column_info.table_id,
                column_info.name,
                limit=100000,
            )
            for value in values:
                value_infos.append(ValueInfo(
                    id=f"{column_info.id}.{value}",
                    value=value,
                    column_id=column_info.id,
                ))
        await self.column_value_es_repository.upsert(value_infos)

    async def _save_metric_info_to_milvus(
        self,
        metric_infos: list[MetricInfo],
    ):
        await self.metric_milvus_repository.ensure_collection()
        points = []
        for metric_info in metric_infos:
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": metric_info.name,
                "payload": metric_info,
            })
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": metric_info.description,
                "payload": metric_info,
            })
            for alias in metric_info.alias:
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": alias,
                    "payload": metric_info,
                })

        embeddings: list[list[float]] = []
        texts = [point["embedding_text"] for point in points]
        for i in range(0, len(texts), 20):
            embeddings.extend(
                await self.embed_client.aembed_documents(texts[i:i + 20])
            )

        await self.metric_milvus_repository.upsert(
            [point["id"] for point in points],
            embeddings,
            [point["payload"] for point in points],
        )
