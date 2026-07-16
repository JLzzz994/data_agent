"""SQL 生成节点。

依据合并后的上下文与用户问题，调用 LLM 生成 SQL。
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


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """生成 SQL。"""
    #  调用 LLM 生成 SQL，写入 state["sql"]
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "生成sql", "status": "running"})
    try:
        logger.info("开始生成sql")
        # 3. 业务逻辑
        # 3.1 获取所需数据
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]

        # 3.2 调用llm生成sql
        prompt = PromptTemplate(template=load_prompt("generate_sql"),
                                input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info"])
        chain = prompt | llm | StrOutputParser()
        sql = await chain.ainvoke({
            "query": query,
            "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
             })
        # 3.3 业务没有异常写回state

        # 3.4 业务异常->校正sql

        # 4. 业务正常 成功
        writer({"type": "progress", "step": "生成sql", "status": "success"})
        logger.info(f"生成SQL成功：{sql}")
        return {"sql": sql}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "生成sql", "status": "error"})
        logger.error(f"生成sql失败{e}")
        raise
