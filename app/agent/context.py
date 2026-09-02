from typing import TypedDict

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.milvus.column_milvus_repository import ColumnMilvusRepository
from app.repositories.milvus.metric_milvus_repository import MetricMilvusRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.security.access_scope import AccessScope


class DataAgentContext(TypedDict):
    meta_mysql_repository: MetaMySQLRepository
    dw_mysql_repository: DWMSQLRepository
    column_milvus_repository: ColumnMilvusRepository
    metric_milvus_repository: MetricMilvusRepository
    column_value_es_repository: ColumnValueESRepository
    embed_client: HuggingFaceEndpointEmbeddings
    access_scope: AccessScope
