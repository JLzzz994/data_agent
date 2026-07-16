"""SQL 校验节点。

对生成的 SQL 进行语法/可用性校验。
"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """校验 SQL。"""
    #  校验 SQL 合法性，
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "校验sql", "status": "running"})
    try:
        logger.info("开始校验sql")
        # 3. 业务逻辑
        sql = state["sql"]
        dw_mysql_repository: DWMSQLRepository = runtime.context["dw_mysql_repository"]
        await dw_mysql_repository.validate_sql(sql)
        logger.info("校验sql成功")

        # 4. 业务正常 成功
        writer({"type": "progress", "step": "校验sql", "status": "success"})
        return {"error": None}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "校验sql", "status": "error"})
        logger.error(f"校验sql失败{e}")
        return {"error": str(e)}
