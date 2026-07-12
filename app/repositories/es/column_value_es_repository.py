from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.entities.value_info import ValueInfo


class ColumnValueESRepository:
    index_name = "data-agent-column"
    es_index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def ensure_index(self):
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name,
                mappings=self.es_index_mappings
            )

    async def upsert(self, value_infos: list[ValueInfo], batch_size: int = 100):
        for i in range(0,len(value_infos),batch_size):
            operations = []
            batch_values = value_infos[i:i+batch_size]
            for value_info in batch_values:
                operations.append({
                    "index":{
                        "_index":self.index_name, # 类属性 表名
                        "_id":value_info.id # 主键 uuid
                    }
                })
                operations.append(asdict(value_info))
            await self.client.bulk(operations=operations)