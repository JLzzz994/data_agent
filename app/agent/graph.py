import asyncio

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import DataAgentContext
from app.agent.nodes.add_extra_context import add_extra_context
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.execute_sql import execute_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.filter_metric import filter_metric
from app.agent.nodes.filter_table import filter_table
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.milvus_client_manager import milvus_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.core.log import logger
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.milvus.column_milvus_repository import ColumnMilvusRepository
from app.repositories.milvus.metric_milvus_repository import MetricMilvusRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.security.access_scope import AccessScope

MAX_CORRECTION_ROUNDS = 3

builder = StateGraph(state_schema=DataAgentState, context_schema=DataAgentContext)
builder.add_node("extract_keywords", extract_keywords)
builder.add_node("recall_column", recall_column)
builder.add_node("recall_metric", recall_metric)
builder.add_node("recall_value", recall_value)
builder.add_node("merge_retrieved_info", merge_retrieved_info)
builder.add_node("filter_table", filter_table)
builder.add_node("filter_metric", filter_metric)
builder.add_node("add_extra_context", add_extra_context)
builder.add_node("generate_sql", generate_sql)
builder.add_node("validate_sql", validate_sql)
builder.add_node("correct_sql", correct_sql)
builder.add_node("execute_sql", execute_sql)

builder.set_entry_point("extract_keywords")
builder.add_edge("extract_keywords", "recall_column")
builder.add_edge("extract_keywords", "recall_metric")
builder.add_edge("extract_keywords", "recall_value")
builder.add_edge(["recall_column", "recall_metric", "recall_value"], "merge_retrieved_info")
builder.add_edge("merge_retrieved_info", "filter_metric")
builder.add_edge("merge_retrieved_info", "filter_table")
builder.add_edge(["filter_metric", "filter_table"], "add_extra_context")
builder.add_edge("add_extra_context", "generate_sql")
builder.add_edge("generate_sql", "validate_sql")


def route_after_validation(state: DataAgentState):
    if not state.get("error"):
        return "execute_sql"
    if state.get("retry_count", 0) >= MAX_CORRECTION_ROUNDS:
        return END
    return "correct_sql"


builder.add_conditional_edges("validate_sql", route_after_validation)
builder.add_edge("correct_sql", "validate_sql")
graph = builder.compile()


if __name__ == "__main__":
    async def test():
        embedding_client_manager.init()
        es_client_manager.init()
        dw_mysql_client_manager.init()
        meta_mysql_client_manager.init()
        milvus_client_manager.init()

        try:
            async with (
                dw_mysql_client_manager.session_factory() as dw_session,
                meta_mysql_client_manager.session_factory() as meta_session,
            ):
                dw_session: AsyncSession
                meta_session: AsyncSession
                context = DataAgentContext(
                    dw_mysql_repository=DWMSQLRepository(dw_session),
                    meta_mysql_repository=MetaMySQLRepository(meta_session),
                    column_milvus_repository=ColumnMilvusRepository(milvus_client_manager.client),
                    embed_client=embedding_client_manager.client,
                    column_value_es_repository=ColumnValueESRepository(es_client_manager.client),
                    metric_milvus_repository=MetricMilvusRepository(milvus_client_manager.client),
                    access_scope=AccessScope(
                        tenant_id="tenant_hc_001",
                        allowed_shop_ids=("shop_tmall_001", "shop_jd_001"),
                    ),
                )
                state = DataAgentState(
                    query="统计最近30天各店铺支付金额、退款金额和退款率，并按支付金额降序",
                    max_rows=500,
                )
                async for chunk in graph.astream(
                    input=state,
                    context=context,
                    stream_mode=["custom"],
                ):
                    print(chunk)
        except Exception as exc:
            logger.error(f"查询业务失败：{exc}")
        finally:
            await es_client_manager.close()
            await dw_mysql_client_manager.close()
            await meta_mysql_client_manager.close()
            await milvus_client_manager.close()

    asyncio.run(test())
