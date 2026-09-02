"""为 SQL 生成补充当前时间与数据库环境。"""
from datetime import datetime
from zoneinfo import ZoneInfo

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DBInfoState, DataAgentState, DateInfoState
from app.core.log import logger

BUSINESS_TIMEZONE = ZoneInfo("Asia/Shanghai")


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "补充上下文", "status": "running"})
    try:
        now = datetime.now(BUSINESS_TIMEZONE)
        date_info = DateInfoState(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            weekday=now.strftime("%A"),
            quarter=f"Q{(now.month - 1) // 3 + 1}",
            timezone="Asia/Shanghai",
        )
        db_info = DBInfoState(**await runtime.context["dw_mysql_repository"].get_db_info())
        writer({"type": "progress", "step": "补充上下文", "status": "success"})
        logger.info(f"补充上下文成功 日期={date_info} 数据库={db_info}")
        return {"date_info": date_info, "db_info": db_info}
    except Exception as exc:
        writer({"type": "progress", "step": "补充上下文", "status": "error"})
        logger.error(f"补充上下文失败: {exc}")
        raise
