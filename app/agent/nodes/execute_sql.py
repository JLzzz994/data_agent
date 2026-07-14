"""SQL 执行节点。

在校验通过后执行 SQL 并获取结果。
"""
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def execute_sql(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """执行 SQL。"""
    #  调用 DWMSQLRepository 执行 SQL，
    writer = runtime.stream_writer
    writer({"type":"progress","step":"执行sql","status":"running"})

    sql = state["sql"]
    dw_mysql_repository = runtime.context["dw_mysql_repository"]
    try:
        logger.info("开始执行sql")
        # 3. 业务逻辑
        result = await dw_mysql_repository.execute_sql(sql)

        writer({"type":"result","data":result})
        logger.info(f"执行sql结果:{result}")
        # 4. 业务正常 成功
        writer({"type": "progress", "step": "执行sql", "status": "success"})
    except RuntimeError as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "执行sql", "status": "error"})
        logger.error(f"执行sql失败{e}")
        raise
