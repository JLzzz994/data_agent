"""添加额外上下文信息节点。

为后续 SQL 生成补充额外的上下文（如时间范围、业务规则等）。
"""
from datetime import datetime

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState, DBInfoState
from app.core.log import logger


async def add_extra_context(state:DataAgentState,runtime:Runtime[DataAgentContext]):
    """补充额外上下文信息。"""
    # 注入额外上下文（时间范围、业务规则等）
    writer = runtime.stream_writer
    writer({"type":"progress","step":"补充上下文","status":"running"})
    try:
        logger.info("开始补充上下文")
        # 3. 业务逻辑
        today = datetime.today()

        quarter = f"Q{(today.month - 1) // 3 + 1}"
        date_info = DateInfoState(
            date=today.strftime("%Y-%m-%d"),
            weekday=today.strftime("%A"),
            quarter=quarter,
        )

        db_info = DBInfoState(**await runtime.context['dw_mysql_repository'].get_db_info())


        # 4. 业务正常 成功
        writer({"type": "progress", "step": "补充上下文", "status": "success"})
        logger.info(f"补充上下文成功 日期是{date_info} 版本是{db_info}")
        return {"date_info": date_info, "db_info": db_info}
    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "补充上下文", "status": "error"})
        logger.error(f"补充上下文失败{e}")
        raise
