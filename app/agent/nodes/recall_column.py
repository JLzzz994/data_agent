"""字段信息召回节点。

依据关键词从向量库召回相关的字段信息。
"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """依据关键词召回相关字段信息。"""
    # 调用 ColumnQdrantRepository 召回字段
    writer = runtime.stream_writer
    writer({"type":"progress","step":"召回字段","status":"running"})
    try:
        logger.info("开始召回字段")
        # 3. 业务逻辑
        # 3.1 获取关键词和 用户问题
        keywords = state["keywords"]
        query = state["query"]
        retrieved_columns_dict:dict[str,ColumnInfo] = {}
        # 3.2 调用llm对关键词进行扩充
        prompt = PromptTemplate(template=load_prompt("extend_keywords_for_column_recall"),input_variables=["query"])
        chain = prompt | llm | JsonOutputParser()
        result = await chain.ainvoke({"query": query})
        keywords = list(set(keywords + result))
        # 3.3 遍历关键词 查询qdrant 召回字段信息
        embed_client = runtime.context["embed_client"]
        column_qdrant_repository = runtime.context["column_qdrant_repository"]
        for keyword in keywords:
            embedding =await embed_client.aembed_query(keyword)
            column_infos:list[ColumnInfo] = await column_qdrant_repository.asearch(embedding)
            for column_info in column_infos:
                if column_info.id not in retrieved_columns_dict:
                    retrieved_columns_dict[column_info.id]=column_info

        # 4. 业务正常 成功
        writer({"type": "progress", "step": "召回字段", "status": "success"})
        logger.info(f"召回字段信息:{retrieved_columns_dict.keys()}")
        return {"recall_columns": list(retrieved_columns_dict.values())}
    except RuntimeError as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "召回字段", "status": "error"})
        logger.error(f"召回字段失败{e}")
        raise
