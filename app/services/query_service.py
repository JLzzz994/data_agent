import json

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
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


    async def query(self,query:str):
        state = DataAgentState(query=query)
        context = DataAgentContext(
            dw_mysql_repository=self.dw_mysql_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            column_qdrant_repository=self.column_qdrant_repository,
            embed_client=self.embed_client,
            column_value_es_repository=self.column_value_es_repository,
            metric_qdrant_repository=self.metric_qdrant_repository
        )

        # context = DataAgentContext()
        try:
            async for chunk in graph.astream(
                    input=state,
                    context=context,
                    # stream_mode=["custom","updates"]
                    stream_mode="custom"
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False,default=str)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False,default=str)}\n\n"
