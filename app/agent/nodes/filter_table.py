"""表格信息过滤节点。

对召回的表/字段信息进行过滤，保留与问题相关的部分。
"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """过滤召回的表/字段信息。"""
    #  过滤无关表与字段
    writer = runtime.stream_writer
    writer({"type":"progress","step":"过滤表/字段信息","status":"running"})
    try:
        logger.info("开始过滤表/字段信息")
        # 3. 业务逻辑
        # 3.1 获取召回的state信息 用户问题
        table_infos:list[TableInfoState] = state["table_infos"]
        query = state["query"]
        # 3.2 调用大模型获取回答问题必须的表和字段
        prompt = PromptTemplate(template=load_prompt("filter_table_info"),input_variables=["query","table_infos"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query":query,"table_infos":table_infos})
        # 3.3 遍历state 删除不需要的表和字段
        # {{
        #     "表名1":["字段1", "字段2", "..."],
        #     "表名2":["字段1", "字段2", "..."]
        # }}
        for table_info in table_infos[:]:
            table_name = table_info["name"]
            if table_name not in result:
                table_infos.remove(table_info)
            else:
                for column in table_info["columns"][:]:
                    if column["name"] not in result[table_name]:
                        table_info["columns"].remove(column)

        # # 外层：过滤表
        # table_infos = [t for t in table_infos if t["name"] in result]
        #
        # # 内层：过滤每张表的列
        # for table in table_infos:
        #     table["columns"] = [c for c in table["columns"] if c["name"] in result[table["name"]]]












        # 4. 业务正常 成功
        writer({"type": "progress", "step": "过滤表/字段信息", "status": "success"})

        logger.info(f"过滤表/字段信息成功:{[table_info["name"]+"."+column_info["name"] for table_info in table_infos for column_info in table_info["columns"]]}")
        return {"table_infos":table_infos}
    except RuntimeError as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "过滤表/字段信息", "status": "error"})
        logger.error(f"过滤表/字段信息失败{e}")

