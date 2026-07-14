from dataclasses import asdict

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.conversions.common_types import VectorParams
from qdrant_client.http.models import PointStruct

from app.conf.app_config import app_config
from app.core.log import logger
from app.entities.metric_info import MetricInfo


class MetricQdrantRepository:
    collection_name: str = "data-agent-metric"

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def ensure_collection(self):
        if not await self.client.collection_exists(collection_name=self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"创建qdrant表{self.collection_name}成功")

    async def upsert(self, ids: list[str], embeddings: list[list[float]], payloads: list[MetricInfo],
                     batch_size: int = 20):
        '''

        :param ids:
        :param embeddings:
        :param payloads:
        :param batch_size:
        :return:
        '''
        zipped = list(zip(ids, embeddings, payloads))
        for i in range(0, len(zipped), batch_size):
            batch = zipped[i:i + batch_size]
            points = [PointStruct(
                id=i,
                vector=embedding,
                payload=asdict(payload)
            ) for i, embedding, payload in batch]
            await self.client.upsert(
                collection_name=self.collection_name
                , points=points
            )

    async def asearch(self, embedding: list[float], score_threshold: float = 0.6, limit: int = 10):
        # points: List["ScoredPoint"]
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            score_threshold=score_threshold,
            limit=limit
        )
        return [MetricInfo(**point.payload) for point in result.points]
