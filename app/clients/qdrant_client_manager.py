import asyncio
from random import random
from typing import Optional

from qdrant_client import AsyncQdrantClient, models

from app.conf.app_config import QdrantConfig, app_config


class QdrantClientManager:
    def __init__(self, config: QdrantConfig):
        self.config = config
        self.client: Optional[AsyncQdrantClient] = None

    def init(self):
        self.client = AsyncQdrantClient(self._get_url())

    async def close(self):
        await self.client.close()

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"


qdrant_client_manager = QdrantClientManager(app_config.qdrant)

if __name__ == '__main__':
    seed = 42
    async def test():
        qdrant_client_manager.init()
        client = qdrant_client_manager.client
        collection_name = "my_collection"

        # 1 Create a collection 开发
        # if not await client.exists(collection_name=collection_name):
        #     await client.create_collection(
        #         collection_name=collection_name,
        #         vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
        #     )

        #1.1 方便测试 每次使用新的集合
        if await client.collection_exists(collection_name=collection_name):
            await client.delete_collection(collection_name=collection_name)
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
        )
        # 2  Insert a vector
        await client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=i,
                    payload={
                        "color": "red" if i % 2 == 0 else "blue",
                    },  # 携带数据
                    vector=[random() for _ in range(1024)],
                )
                for i in range(100)
            ],
        )

        # 搜索相似的向量
        result = await client.query_points(
            collection_name=collection_name,
            query=[random() for _ in range(1024)],
            limit=2,
            score_threshold=0.7,
            query_filter=models.Filter(
                # must=[models.FieldCondition(key="color", match=models.MatchValue(value="red"))]
                must=[models.FieldCondition(key="color", match=models.MatchText(text="red"))]
            ) # 根据携带的payload数据进行过滤
        )
        # print(result.points)

        for point in result.points:
            print(point.payload)
        await qdrant_client_manager.close()

    asyncio.run(test())