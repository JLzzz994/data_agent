import asyncio
import uuid
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.conf.load_config import load_config
from app.conf.meta_config import MetaConfig, TableConfig, meta_config, MetricConfig
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
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledgeService:
    def __init__(self,
                 dw_mysql_repository: DWMSQLRepository,
                 meta_mysql_repository: MetaMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 embed_client: HuggingFaceEndpointEmbeddings,
                 column_value_es_repository: ColumnValueESRepository,
                 metric_qdrant_repository:MetricQdrantRepository,

                 ):
        self.dw_mysql_repository = dw_mysql_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embed_client = embed_client
        self.column_value_es_repository = column_value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository
    async def build(self, config_file: Path):
        # 1. 加载配置文件
        meta_config: MetaConfig = load_config(config_file, MetaConfig)
        # logger.info(meta_config.tables)
        # 2. 处理表信息
        if meta_config.tables:
            # 2.1 保存表信息到meta数据库
            column_infos: list[ColumnInfo] = await self._save_table_infos_to_meta_db(meta_config.tables)
            logger.info(f"保存表元数据到meta库成功")
            # 2.2 为字段信息建立向量索引
            await self._save_column_info_to_dqrant(column_infos)
            logger.info(f"表字段信息存入向量库成功")
            # 2.3 为字段值建立全文索引
            await self._save_column_values_to_es(column_infos)
            logger.info(f"表字段值信息存入ElasticSearch成功")
        # 3. 处理指标信息
        if meta_config.metrics:
            metric_infos: list[MetricInfo] = await self._save_metric_infos_to_meta_db(meta_config.metrics)
            logger.info(f"保存指标元数据到meta库成功")
        # 3.1 保存指标信息到meta数据库
        # 3.2 为指标信息建立向量索引
            await self._save_metric_info_to_qdrant(metric_infos)
            logger.info(f"保存指标信息到向量库成功")

    async def _save_table_infos_to_meta_db(self, tables: list[TableConfig]) -> list[ColumnInfo]:
        '''
        将表信息和字段信息保存到meta库(table_info column_info)
        :param tables:
        :return:
        '''
        table_infos: list[TableInfoMySQL] = []
        column_infos: list[ColumnInfoMySQL] = []

        for table in tables:
            table_info = TableInfoMySQL(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description
            )
            table_infos.append(table_info)
            # 查询dw中指定表的所有字段类型 dict[字段名:字段类型
            column_type_dict: dict[str, str] = await self.dw_mysql_repository.get_column_types(table.name)
            for column in table.columns:
                # 查询dw库,取出指定字段的前10条数据
                examples: list = await self.dw_mysql_repository.get_column_values(table.name, column.name)
                column_info = ColumnInfoMySQL(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_type_dict[column.name],
                    role=column.role,
                    examples=examples,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )

                column_infos.append(column_info)

        self.meta_mysql_repository.save_table_infos(table_infos)
        self.meta_mysql_repository.save_column_infos(column_infos)
        return [ColumnInfoMapper.to_entity(column_info) for column_info in column_infos]

    async def _save_metric_infos_to_meta_db(self, metrics: list[MetricConfig]) -> list[MetricInfo]:
        '''
        将指标元数据保存到meta库 metric_info column_metric
        :param metrics:
        :return:
        '''
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
                    metric_id=metric.name
                ))
        self.meta_mysql_repository.save_metric_infos(metric_infos)
        self.meta_mysql_repository.save_column_metrics(column_metrics)

        return [MetricInfoMapper.to_entity(metric_info) for metric_info in metric_infos]

    async def _save_column_info_to_dqrant(self, column_infos: list[ColumnInfo]):
        '''
        准备 1.向量id 2.向量 3.元数据payload{字段名称,描述,别名}
        :param column_infos:
        :return:
        '''
        await self.column_qdrant_repository.ensure_collection()
        points = []
        # 1. 创建列表 保存向量点信息

        # 2. 遍历字段信息 构造pyload 字典结构
        for column_info in column_infos:
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": column_info.name,
                "payload": column_info
            })
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": column_info.description,
                "payload": column_info
            })
            for alia in column_info.alias:
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": alia,
                    "payload": column_info
                })
        # 3. 将文本转为向量 分批次处理
        embeddings: list[list[float]] = []
        # 3.1 获取points中待转向量的文本
        texts = [point["embedding_text"] for point in points]
        # 3.2 每批次转20个文本向量
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embed = await self.embed_client.aembed_documents(batch_texts)
            embeddings.extend(batch_embed)
        # 4. 得到持久层需要的 向量点 信息
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_column_values_to_es(self, column_infos: list[ColumnInfo]):
        """
        将部分字段的值 构建索引库文档对象存入ES
        :param column_infos: 字段信息列表
        :return:
        """
        # 1. 创建索引
        await self.column_value_es_repository.ensure_index()
        # 2. 创建文档对象列表 将yaml中sync=true的字段建立全文索引
        need_column_names = [column.name for table in meta_config.tables for column in table.columns if column.sync]
        value_infos = []
        for column_info in column_infos:
            if column_info.name in need_column_names:
                values: list[str] = await self.dw_mysql_repository.get_column_values(column_info.table_id,
                                                                                     column_info.name, limit=1000000)
                for value in values:
                    value_info = ValueInfo(id=str(uuid.uuid4()), value=value, column_id=column_info.id)
                    value_infos.append(value_info)
        # 3. 持久层存储
        await self.column_value_es_repository.upsert(value_infos)

    async def _save_metric_info_to_qdrant(self, metric_infos:list[MetricInfo]):
        '''

        :param metric_infos:
        :return:
        '''
        await self.metric_qdrant_repository.ensure_collection()
        points = []
        # 1. 创建列表 保存向量点信息

        # 2. 遍历字段信息 构造pyload 字典结构
        for metric_info in metric_infos:
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": metric_info.name,
                "payload": metric_info
            })
            points.append({
                "id": str(uuid.uuid4()),
                "embedding_text": metric_info.description,
                "payload": metric_info
            })
            for alia in metric_info.alias:
                points.append({
                    "id": str(uuid.uuid4()),
                    "embedding_text": alia,
                    "payload": metric_info
                })
        # 3. 将文本转为向量 分批次处理
        embeddings: list[list[float]] = []
        # 3.1 获取points中待转向量的文本
        texts = [point["embedding_text"] for point in points]
        # 3.2 每批次转20个文本向量
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embed = await self.embed_client.aembed_documents(batch_texts)
            embeddings.extend(batch_embed)
        # 4. 得到持久层需要的 向量点 信息
        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]
        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)

if __name__ == '__main__':
    meta_knowledge_service = MetaKnowledgeService()
    config_file = Path(__file__).parents[2] / "conf" / "meta_config.yaml"
    asyncio.run(meta_knowledge_service.build(config_file))
