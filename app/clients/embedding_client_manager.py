import asyncio
from typing import Optional

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self,config: EmbeddingConfig):
        self.config = config
        self.client: Optional[HuggingFaceEndpointEmbeddings] = None

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = HuggingFaceEndpointEmbeddings(model=self._get_url())

embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == '__main__':
    async def test():
        embedding_client_manager.init()
        #异步单条数据向量化
        result = await embedding_client_manager.client.aembed_query("hello world")
        print(result)
        print(len(result))

        # 异步批量向量化
        result = await embedding_client_manager.client.aembed_documents(["hello world","end the day"])
        print(result,)
        print(len(result))
    asyncio.run(test())