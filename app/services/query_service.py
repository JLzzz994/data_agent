import json

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.milvus.column_milvus_repository import ColumnMilvusRepository
from app.repositories.milvus.metric_milvus_repository import MetricMilvusRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.security.access_scope import AccessScope


class QueryService:
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

    async def query(
        self,
        query: str,
        access_scope: AccessScope,
        max_rows: int = 500,
    ):
        state = DataAgentState(query=query, max_rows=max_rows)
        context = DataAgentContext(
            dw_mysql_repository=self.dw_mysql_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            column_milvus_repository=self.column_milvus_repository,
            embed_client=self.embed_client,
            column_value_es_repository=self.column_value_es_repository,
            metric_milvus_repository=self.metric_milvus_repository,
            access_scope=access_scope,
        )
        try:
            async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
        except Exception as exc:
            yield "data: " + json.dumps(
                {"type": "error", "message": str(exc)},
                ensure_ascii=False,
                default=str,
            ) + "\n\n"
