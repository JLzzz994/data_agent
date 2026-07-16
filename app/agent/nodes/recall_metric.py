"""指标信息召回节点。

依据关键词从向量库召回相关的指标信息。
"""
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
    """依据关键词召回相关指标信息。"""
    #  调用 MetricQdrantRepository 召回指标
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})
    try:
        logger.info("开始召回指标")
        # 3. 业务逻辑
        # 3.1 从state中获取关键词列表(包含用户原始问题) 获取用户问题
        keywords = state["keywords"]
        query = state["query"]
        # 3.2 调用llm对关键词进行扩充
        # 3.2.1 加载提示词
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_metric_recall"), input_variables=["query"])
        # 3.2.2 创建chain 提示词 | llm | 结果解析
        chain = prompt | llm | JsonOutputParser()
        # 3.2.3 调用chain 获取到扩充后的关键词列表 + 原有关键词
        result = await chain.ainvoke({"query": query})
        keywords = list(set(keywords + result))

        retrieved_metrics_dict: dict[str, MetricInfo] = {}
        embed_client = runtime.context["embed_client"]
        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
        for keyword in keywords:
            embedding = await embed_client.aembed_query(keyword)
            metric_infos: list[MetricInfo] = await metric_qdrant_repository.asearch(embedding)
            for metric_info in metric_infos:
                metric_id = metric_info.id  # f"{table.name}.{column.name}"
                if metric_id not in retrieved_metrics_dict:
                    retrieved_metrics_dict[metric_id] = metric_info
        # 4. 业务正常 成功

        writer({"type": "progress", "step": "召回指标", "status": "success"})
        logger.info(f"召回指标信息:{retrieved_metrics_dict.keys()}")
        return {"recall_metrics": list(retrieved_metrics_dict.values())}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "召回指标", "status": "error"})
        logger.error(f"召回指标失败{e}")
        raise

