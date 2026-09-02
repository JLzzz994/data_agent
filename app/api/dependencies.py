from async_lru import alru_cache
from fastapi import Depends
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.milvus_client_manager import milvus_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.milvus.column_milvus_repository import ColumnMilvusRepository
from app.repositories.milvus.metric_milvus_repository import MetricMilvusRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.services.query_service import QueryService


async def get_dw_mysql_session():
    async with dw_mysql_client_manager.session_factory() as session:
        yield session


async def get_meta_mysql_session():
    async with meta_mysql_client_manager.session_factory() as session:
        yield session


async def get_dw_mysql_repository(session: AsyncSession = Depends(get_dw_mysql_session)):
    return DWMSQLRepository(session)


async def get_meta_mysql_repository(session: AsyncSession = Depends(get_meta_mysql_session)):
    return MetaMySQLRepository(session)


@alru_cache()
async def get_column_milvus_repository():
    return ColumnMilvusRepository(milvus_client_manager.client)


@alru_cache()
async def get_metric_milvus_repository():
    return MetricMilvusRepository(milvus_client_manager.client)


async def get_embed_client():
    return embedding_client_manager.client


@alru_cache()
async def get_column_value_es_repository():
    return ColumnValueESRepository(es_client_manager.client)


async def get_query_service(
    dw_mysql_repository: DWMSQLRepository = Depends(get_dw_mysql_repository),
    meta_mysql_repository: MetaMySQLRepository = Depends(get_meta_mysql_repository),
    column_milvus_repository: ColumnMilvusRepository = Depends(get_column_milvus_repository),
    embed_client: HuggingFaceEndpointEmbeddings = Depends(get_embed_client),
    column_value_es_repository: ColumnValueESRepository = Depends(get_column_value_es_repository),
    metric_milvus_repository: MetricMilvusRepository = Depends(get_metric_milvus_repository),
) -> QueryService:
    return QueryService(
        dw_mysql_repository=dw_mysql_repository,
        meta_mysql_repository=meta_mysql_repository,
        column_milvus_repository=column_milvus_repository,
        embed_client=embed_client,
        column_value_es_repository=column_value_es_repository,
        metric_milvus_repository=metric_milvus_repository,
    )
