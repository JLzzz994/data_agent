import asyncio
from argparse import ArgumentParser
from pathlib import Path

from sqlalchemy.ext.asyncio.session import AsyncSession

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.mysql_client_manager import dw_mysql_client_manager, meta_mysql_client_manager
from app.core.log import logger
from app.repositories.es.column_value_es_repository import ColumnValueESRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.mysql.dw_mysql_repository import DWMSQLRepository
from app.repositories.mysql.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def build(config_path):
    logger.info("开始构建元数据")
    # 1. 执行各个客户端初始化方法
    dw_mysql_client_manager.init()
    meta_mysql_client_manager.init()
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    async with (dw_mysql_client_manager.session_factory() as dw_session, meta_mysql_client_manager.session_factory() as meta_session):
        dw_session:AsyncSession
        meta_session:AsyncSession
        # 2. 创建持久层对象
        dw_mysql_repository = DWMSQLRepository(dw_session)
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        embed_client = embedding_client_manager.client
        column_value_es_repository = ColumnValueESRepository(es_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
        # 3. 将持久层对象传入业务层对象
        meta_knowledge_service = MetaKnowledgeService(
            dw_mysql_repository=dw_mysql_repository,
            meta_mysql_repository=meta_mysql_repository,
            column_qdrant_repository=column_qdrant_repository,
            embed_client=embed_client,
            column_value_es_repository=column_value_es_repository,
            metric_qdrant_repository=metric_qdrant_repository
        )
        # 4. 调用业务层核心业务处理 背后操作mysql,es,qdrant新增操作
        try:
            # 4.1 开启事务
            await dw_session.begin()
            await meta_session.begin()
            # 4.2 调用业务逻辑
            await meta_knowledge_service.build(config_path)
            # 4.3 将mysql,es,qdrant
            await dw_session.commit()
            await meta_session.commit()
            logger.info("元数据构建完成")
        except Exception as e:
            logger.error(f"元数据构建失败{e}")
            await dw_session.rollback()
            await meta_session.rollback()
        finally:
            await dw_mysql_client_manager.close()
            await meta_mysql_client_manager.close()
            await es_client_manager.close()
            await qdrant_client_manager.close()

if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('-c', '--conf')  # option that takes a value

    args = parser.parse_args()
    config_path = Path(args.conf)
    asyncio.run(build(config_path))
