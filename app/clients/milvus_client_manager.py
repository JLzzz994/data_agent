import asyncio
from typing import Optional

from pymilvus import MilvusClient

from app.conf.app_config import MilvusConfig, app_config


class MilvusClientManager:
    def __init__(self, config: MilvusConfig):
        self.config = config
        self.client: Optional[MilvusClient] = None

    def init(self):
        kwargs = {"uri": f"http://{self.config.host}:{self.config.port}"}
        if self.config.token:
            kwargs["token"] = self.config.token
        self.client = MilvusClient(**kwargs)

    async def close(self):
        if self.client is not None:
            await asyncio.to_thread(self.client.close)
            self.client = None


milvus_client_manager = MilvusClientManager(app_config.milvus)
