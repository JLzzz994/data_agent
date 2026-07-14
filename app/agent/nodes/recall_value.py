"""字段取值召回节点。

依据关键词从 ES 全文索引召回字段的可能取值。
"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt


async def recall_value(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """依据关键词召回字段取值。"""
    #  调用 ColumnValueESRepository 召回字段取值
    writer = runtime.stream_writer
    writer({"type":"progress","step":"召回字段取值","status":"running"})
    try:
        logger.info("开始召回字段取值")
        # 3. 业务逻辑
        # 3.1 获取关键词和 用户问题
        keywords = state["keywords"]
        query = state["query"]
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_value_recall"),input_variables=["query"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query": query})
        keywords = list(set(keywords + result))
        column_value_es_repository = runtime.context["column_value_es_repository"]
        column_value_dict:dict[str,ValueInfo]={}
        for keyword in keywords:
            values:list[ValueInfo] = await column_value_es_repository.asearch(keyword)
            for value in values:
                if value.id not in column_value_dict:
                    column_value_dict[value.id] = value

        # 4. 业务正常 成功
        writer({"type": "progress", "step": "召回字段取值", "status": "success"})
        logger.info(f"召回字段取值成功，为{column_value_dict.values()}")
        return {"recall_values": list(column_value_dict.values())}
    except RuntimeError as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "召回字段取值", "status": "error"})
        logger.error(f"召回字段取值失败{e}")
        raise
