"""指标信息过滤节点。

对召回的指标信息进行过滤，保留与问题相关的部分。
"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from app.agent.llm import llm
from app.agent.state import DataAgentState, MetricInfoState

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.evaluation_trace import emit_evaluation_trace
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_metric(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """过滤召回的指标信息。"""
    # 过滤无关指标
    writer = runtime.stream_writer
    writer({"type":"progress","step":"过滤指标","status":"running"})
    try:
        logger.info("开始过滤指标")
        # 3. 业务逻辑
        # 3.1 获取已召回指标信息state列表 获取用户原始问题
        metric_info_states: list[MetricInfoState] = state["metric_infos"]
        # 3.2 调用llm获取需要的指标信息
        prompt = PromptTemplate(template=load_prompt("filter_metric_info"),input_variables=["query","metric_infos"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query":state["query"],"metric_infos":metric_info_states})
        # 3.3 遍历指标列表 移除不需要的指标
        for metric_info_state in metric_info_states[:]:
            metric_name = metric_info_state["name"]
            if metric_name not in result:
                metric_info_states.remove(metric_info_state)

        # metric_info_states = [m for m in metric_info_states if m["name"] in result]
        # 4. 业务正常 成功
        writer({"type": "progress", "step": "过滤指标", "status": "success"})
        emit_evaluation_trace(
            writer,
            "filtered_metrics",
            metrics=[metric_info["name"] for metric_info in metric_info_states],
        )
        logger.info(f"过滤指标成功:{metric_info_states}")
        return {"metric_infos": metric_info_states}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "过滤指标", "status": "error"})
        logger.error(f"过滤指标失败{e}")
        raise

