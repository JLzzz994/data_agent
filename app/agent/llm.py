"""LLM 客户端定义。

参考 app/clients/embedding_client_manager.py 的管理器模式，
依据 app_config.llm 配置初始化并对外暴露 LLM 客户端实例。
"""
import asyncio

from langchain.chat_models import init_chat_model

from app.conf.app_config import LLMConfig, app_config

llm = init_chat_model(
    model=app_config.llm.model_name,
    api_key=app_config.llm.api_key,
    temperature=0,
)

if __name__ == '__main__':

    for chunk in llm.stream("你是什么模型"):
        print(chunk.text,end="",flush=True)

