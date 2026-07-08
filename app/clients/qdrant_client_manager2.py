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

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    async def close(self):
        await self.client.close()

qdrant_client_manager = QdrantClientManager(app_config.qdrant)

if __name__ == '__main__':
    async def test():
        qdrant_client_manager.init()
        client = qdrant_client_manager.client

        # 1.Create a collection
        collection_name = "my_collection"

        # 1.1 开发 不存在表才创建
        # if not await client.exists(collection_name=collection_name):
        #     await client.create_collection(
        #         collection_name=collection_name,
        #         vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
        #     )

        # 1.2 测试 每次使用新的表
        if await client.collection_exists(collection_name=collection_name):
           await client.delete_collection(collection_name=collection_name)
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
        )

        # 2. Insert a vector
        await client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=i,
                    payload={
                        "color": "red" if i % 2 == 0 else "blue",
                    },
                    vector=[random() for _ in range(1024)],
                )
                for i in range(100)
            ],
        )

        #3. Search for nearest neighbors
        result = await client.query_points(
            collection_name=collection_name,
            query=[random() for _ in range(1024)],
            limit=3,
            score_threshold=0.7,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="color",match=models.MatchValue(value="red"))]
            )
        )
        for point in result.points:
            print(point.payload)

        await qdrant_client_manager.close()

    asyncio.run(test())