"""依据关键词从 Milvus 召回相关指标信息。"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})
    try:
        query = state["query"]
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_metric_recall"),
            input_variables=["query"],
        )
        result = await (prompt | llm | JsonOutputParser()).ainvoke({"query": query})
        keywords = list(set(state["keywords"] + result))

        retrieved: dict[str, MetricInfo] = {}
        repo = runtime.context["metric_milvus_repository"]
        embed_client = runtime.context["embed_client"]
        for keyword in keywords:
            embedding = await embed_client.aembed_query(keyword)
            for metric_info in await repo.asearch(embedding):
                retrieved.setdefault(metric_info.id, metric_info)

        writer({"type": "progress", "step": "召回指标", "status": "success"})
        logger.info(f"Milvus 召回指标: {retrieved.keys()}")
        return {"recall_metrics": list(retrieved.values())}
    except Exception as exc:
        writer({"type": "progress", "step": "召回指标", "status": "error"})
        logger.error(f"召回指标失败: {exc}")
        raise
