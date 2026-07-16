"""SQL 校正节点。

依据校验失败信息，调用 LLM 对 SQL 进行校正。
"""
import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """校正 SQL。"""
    #  依据校验错误校正 SQL，更新 state["sql"]
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "修正sql", "status": "running"})
    try:
        logger.info("开始修正sql")
        # 3. 业务逻辑

        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]
        sql = state["sql"]
        error = state["error"]
        # 3.2 调用llm生成sql
        prompt = PromptTemplate(template=load_prompt("correct_sql"),
                                input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info", "sql",
                                                 "error"])
        chain = prompt | llm | StrOutputParser()
        sql = await chain.ainvoke({
            "query": query,
            "error": error,
            "sql": sql,
            "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
        })

        # 4. 业务正常 成功
        writer({"type": "progress", "step": "修正sql", "status": "success"})
        logger.info(f"修正sql成功{sql}")
        return {"sql": sql}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "修正sql", "status": "error"})
        logger.error(f"修正sql失败{e}")
        raise
