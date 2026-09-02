"""在三层校验通过后执行只读 SQL，并统一脱敏后返回。"""
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.security.result_masking import mask_rows


async def execute_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "执行sql", "status": "running"})
    try:
        max_rows = state.get("max_rows", 500)
        result = await runtime.context["dw_mysql_repository"].execute_sql(state["sql"], max_rows=max_rows)
        result = mask_rows(result)
        writer({
            "type": "result",
            "data": result,
            "meta": {"rows": len(result), "max_rows": max_rows, "masked": True},
        })
        writer({"type": "progress", "step": "执行sql", "status": "success"})
        logger.info(f"执行sql完成，返回 {len(result)} 行")
    except Exception as exc:
        writer({"type": "progress", "step": "执行sql", "status": "error"})
        logger.error(f"执行sql失败: {exc}")
        raise
