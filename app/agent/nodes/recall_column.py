"""依据关键词从 Milvus 召回相关字段信息。"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段", "status": "running"})
    try:
        query = state["query"]
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        )
        result = await (prompt | llm | JsonOutputParser()).ainvoke({"query": query})
        keywords = list(set(state["keywords"] + result))

        retrieved: dict[str, ColumnInfo] = {}
        repo = runtime.context["column_milvus_repository"]
        embed_client = runtime.context["embed_client"]
        for keyword in keywords:
            embedding = await embed_client.aembed_query(keyword)
            for column_info in await repo.asearch(embedding):
                retrieved.setdefault(column_info.id, column_info)

        writer({"type": "progress", "step": "召回字段", "status": "success"})
        logger.info(f"Milvus 召回字段: {retrieved.keys()}")
        return {"recall_columns": list(retrieved.values())}
    except Exception as exc:
        writer({"type": "progress", "step": "召回字段", "status": "error"})
        logger.error(f"召回字段失败: {exc}")
        raise
