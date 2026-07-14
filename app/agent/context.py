"""langgraph 运行上下文定义。

封装 agent 图运行期间所需的外部依赖（LLM、各 repository、各 client 等），
便于在节点中以依赖注入的方式访问，而非依赖全局单例。
"""
from typing import TypedDict

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository





class DataAgentContext(TypedDict):
    """Agent 运行上下文，持有各节点运行所需依赖。"""

    # llm: ...
    meta_mysql_repository: MetaMySQLRepository
    dw_mysql_repository: DWMSQLRepository
    column_qdrant_repository: ColumnQdrantRepository
    metric_qdrant_repository: MetricQdrantRepository
    column_value_es_repository: ColumnValueESRepository
    embed_client:HuggingFaceEndpointEmbeddings

