import asyncio
import json
from dataclasses import asdict

from pymilvus import DataType, MilvusClient

from app.conf.app_config import app_config
from app.core.log import logger
from app.entities.column_info import ColumnInfo


def _json_safe(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class ColumnMilvusRepository:
    collection_name = "huice_data_agent_column"

    def __init__(self, client: MilvusClient):
        self.client = client

    async def ensure_collection(self):
        exists = await asyncio.to_thread(
            self.client.has_collection,
            collection_name=self.collection_name,
        )
        if exists:
            return
        await asyncio.to_thread(
            self.client.create_collection,
            collection_name=self.collection_name,
            dimension=app_config.milvus.embedding_size,
            primary_field_name="pk",
            id_type=DataType.VARCHAR,
            vector_field_name="vector",
            metric_type="COSINE",
            auto_id=False,
            max_length=64,
            enable_dynamic_field=True,
        )
        logger.info(f"创建 Milvus collection {self.collection_name} 成功")

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[ColumnInfo],
        batch_size: int = 50,
    ):
        rows = [
            {"pk": point_id, "vector": vector, **_json_safe(asdict(payload))}
            for point_id, vector, payload in zip(ids, embeddings, payloads)
        ]
        for i in range(0, len(rows), batch_size):
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                data=rows[i:i + batch_size],
            )

    async def asearch(
        self,
        embedding: list[float],
        score_threshold: float = 0.6,
        limit: int = 10,
    ) -> list[ColumnInfo]:
        result = await asyncio.to_thread(
            self.client.search,
            collection_name=self.collection_name,
            data=[embedding],
            limit=limit,
            output_fields=[
                "id", "name", "type", "role", "examples",
                "description", "alias", "table_id",
            ],
        )
        hits = result[0] if result else []
        columns = []
        for hit in hits:
            if hit.get("distance", 0) < score_threshold:
                continue
            entity = hit.get("entity", {})
            columns.append(ColumnInfo(
                id=entity["id"],
                name=entity["name"],
                type=entity["type"],
                role=entity["role"],
                examples=entity.get("examples", []),
                description=entity.get("description", ""),
                alias=entity.get("alias", []),
                table_id=entity["table_id"],
            ))
        return columns
