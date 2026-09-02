"""SQL 校验：静态安全、EXPLAIN、LLM 语义一致性、确定性数据权限注入。"""
import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt
from app.security.scoped_sql import apply_access_scope

MAX_CORRECTION_ROUNDS = 3


async def _semantic_validate(state: DataAgentState) -> str:
    prompt = PromptTemplate(
        template=load_prompt("validate_sql_semantics"),
        input_variables=["query", "sql", "table_infos", "metric_infos", "date_info", "db_info"],
    )
    result = await (prompt | llm | StrOutputParser()).ainvoke({
        "query": state["query"],
        "sql": state["sql"],
        "table_infos": yaml.dump(state["table_infos"], allow_unicode=True, sort_keys=False),
        "metric_infos": yaml.dump(state["metric_infos"], allow_unicode=True, sort_keys=False),
        "date_info": yaml.dump(state["date_info"], allow_unicode=True, sort_keys=False),
        "db_info": yaml.dump(state["db_info"], allow_unicode=True, sort_keys=False),
    })
    return result.strip()


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    retry_count = state.get("retry_count", 0)
    raw_sql = state["sql"]
    repository = runtime.context["dw_mysql_repository"]

    writer({"type": "progress", "step": "校验sql", "status": "running", "round": retry_count})
    try:
        # 1) SQLGlot 只读静态校验 + 2) 真实 MySQL EXPLAIN
        await repository.validate_sql(raw_sql)
        writer({"type": "validation", "stage": "static+explain", "status": "success"})

        # 3) LLM 只判断业务语义，不负责权限。
        writer({"type": "validation", "stage": "semantic", "status": "running"})
        semantic_result = await _semantic_validate(state)
        if semantic_result != "PASS":
            reason = semantic_result.removeprefix("FAIL:").strip()
            raise ValueError(f"语义一致性校验失败: {reason or semantic_result}")
        writer({"type": "validation", "stage": "semantic", "status": "success"})

        # 4) 由确定性代码注入 tenant/shop 权限，并再次 EXPLAIN。
        scoped_sql = apply_access_scope(
            raw_sql,
            runtime.context["access_scope"],
            dialect=state["db_info"]["dialect"],
        )
        await repository.validate_sql(scoped_sql)
        writer({"type": "validation", "stage": "access_scope", "status": "success"})

        writer({"type": "progress", "step": "校验sql", "status": "success", "round": retry_count})
        return {
            "sql": scoped_sql,
            "error": None,
            "validation_stage": "passed",
            "semantic_validation": semantic_result,
        }
    except PermissionError as exc:
        error = f"数据权限拒绝: {exc}"
        writer({
            "type": "validation",
            "stage": "access_scope",
            "status": "rejected",
            "message": error,
        })
        writer({
            "type": "result",
            "status": "rejected",
            "message": error,
        })
        logger.warning(error)
        return {
            "error": error,
            "retry_count": MAX_CORRECTION_ROUNDS,
            "validation_stage": "access_denied",
            "semantic_validation": None,
        }
    except Exception as exc:
        error = str(exc)
        exhausted = retry_count >= MAX_CORRECTION_ROUNDS
        writer({
            "type": "progress",
            "step": "校验sql",
            "status": "error",
            "round": retry_count,
            "message": error,
        })
        if exhausted:
            writer({
                "type": "result",
                "status": "rejected",
                "message": f"SQL 自动纠错已达到 {MAX_CORRECTION_ROUNDS} 轮，拒绝执行",
                "error": error,
            })
        logger.error(f"校验sql失败: {error}")
        return {
            "error": error,
            "validation_stage": "failed",
            "semantic_validation": None,
        }
