"""仅在评测模式开启的 SSE trace，默认不向普通请求暴露内部 SQL。"""
import os
from typing import Any


def evaluation_trace_enabled() -> bool:
    return os.getenv("DATA_AGENT_EVAL_TRACE", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def emit_evaluation_trace(writer, stage: str, **payload: Any) -> None:
    if evaluation_trace_enabled():
        writer({"type": "eval_trace", "stage": stage, **payload})
