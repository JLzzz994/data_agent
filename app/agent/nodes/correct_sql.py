"""依据校验失败信息对 SQL 做最小必要修正。"""
import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.nodes.generate_sql import _clean_sql
from app.agent.state import DataAgentState
from app.core.evaluation_trace import emit_evaluation_trace
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    retry_count = state.get("retry_count", 0) + 1
    writer({"type": "progress", "step": "修正sql", "status": "running", "round": retry_count})
    try:
        prompt = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info", "sql", "error"],
        )
        chain = prompt | llm | StrOutputParser()
        sql = await chain.ainvoke({
            "query": state["query"],
            "error": state["error"],
            "sql": state["sql"],
            "table_infos": yaml.dump(state["table_infos"], allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(state["metric_infos"], allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(state["db_info"], allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(state["date_info"], allow_unicode=True, sort_keys=False),
        })
        sql = _clean_sql(sql)
        writer({"type": "progress", "step": "修正sql", "status": "success", "round": retry_count})
        emit_evaluation_trace(writer, "corrected_sql", round=retry_count, sql=sql)
        logger.info(f"第{retry_count}轮修正SQL成功: {sql}")
        return {"sql": sql, "retry_count": retry_count}
    except Exception as exc:
        writer({"type": "progress", "step": "修正sql", "status": "error", "round": retry_count})
        logger.error(f"修正sql失败: {exc}")
        raise
