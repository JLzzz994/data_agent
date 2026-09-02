"""SQL 生成节点。"""
import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.evaluation_trace import emit_evaluation_trace
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


def _clean_sql(text: str) -> str:
    sql = text.strip()
    if sql.startswith("```") and sql.endswith("```"):
        sql = sql.strip("`").strip()
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
    return sql.rstrip(";").strip()


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "生成sql", "status": "running"})
    try:
        prompt = PromptTemplate(
            template=load_prompt("generate_sql"),
            input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info"],
        )
        chain = prompt | llm | StrOutputParser()
        sql = await chain.ainvoke({
            "query": state["query"],
            "table_infos": yaml.dump(state["table_infos"], allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(state["metric_infos"], allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(state["db_info"], allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(state["date_info"], allow_unicode=True, sort_keys=False),
        })
        sql = _clean_sql(sql)
        writer({"type": "progress", "step": "生成sql", "status": "success"})
        emit_evaluation_trace(writer, "generated_sql", sql=sql)
        logger.info(f"生成SQL成功：{sql}")
        return {"sql": sql, "retry_count": 0, "error": None}
    except Exception as exc:
        writer({"type": "progress", "step": "生成sql", "status": "error"})
        logger.error(f"生成sql失败: {exc}")
        raise
