import asyncio
from argparse import ArgumentParser
from pathlib import Path

from sqlalchemy.ext.asyncio.session import AsyncSession

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.milvus_client_manager import milvus_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.core.log import logger
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.milvus.column_milvus_repository import ColumnMilvusRepository
from app.repositories.milvus.metric_milvus_repository import MetricMilvusRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build(config_path: Path):
    logger.info("开始构建慧经营问数元数据")
    dw_mysql_client_manager.init()
    meta_mysql_client_manager.init()
    milvus_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    async with (
        dw_mysql_client_manager.session_factory() as dw_session,
        meta_mysql_client_manager.session_factory() as meta_session,
    ):
        dw_session: AsyncSession
        meta_session: AsyncSession
        service = MetaKnowledgeService(
            dw_mysql_repository=DWMSQLRepository(dw_session),
            meta_mysql_repository=MetaMySQLRepository(meta_session),
            column_milvus_repository=ColumnMilvusRepository(milvus_client_manager.client),
            embed_client=embedding_client_manager.client,
            column_value_es_repository=ColumnValueESRepository(es_client_manager.client),
            metric_milvus_repository=MetricMilvusRepository(milvus_client_manager.client),
        )
        try:
            await dw_session.begin()
            await meta_session.begin()
            await service.build(config_path)
            await dw_session.commit()
            await meta_session.commit()
            logger.info("元数据构建完成")
        except Exception as exc:
            logger.error(f"元数据构建失败: {exc}")
            await dw_session.rollback()
            await meta_session.rollback()
            raise
        finally:
            await dw_mysql_client_manager.close()
            await meta_mysql_client_manager.close()
            await es_client_manager.close()
            await milvus_client_manager.close()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--conf", required=True)
    args = parser.parse_args()
    asyncio.run(build(Path(args.conf)))
