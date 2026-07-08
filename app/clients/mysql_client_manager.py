import asyncio

from typing import Optional

from sqlalchemy import text, Select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.conf.app_config import DBConfig, app_config
from app.models.mysql.table_info_mysql import TableInfoMySQL


# from sqlalchemy.ext.asyncio import create_async_engine
#
# engine = create_async_engine(
#     "mysql+asyncmy://user:pass@hostname/dbname?charset=utf8mb4"
# )

class MySQLClientManager:
    def __init__(self, config: DBConfig):
        self.config = config
        self.client: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None

    def init(self):
        self.client = create_async_engine(self._get_url(), pool_size=10, max_overflow=5)

        self.session_factory = async_sessionmaker(
            self.client,
            autoflush=False,
            autobegin=True,
        )

    async def close(self):
        await self.client.dispose()

    def _get_url(self):
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}/{self.config.database}?charset=utf8mb4"


dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)

if __name__ == '__main__':
    # async def test():
    #     # 初始化客户端
    #     dw_mysql_client_manager.init()
    #     # 创建异步会话
    #     # autoflush=False 前面未提交的更新数据 当前查询不能未提交的数据
    #     # autobegin=True 自动开启事物
    #     # async with AsyncSession(dw_mysql_client_manager.client, autoflush=False, autobegin=True) as session:
    #     # assert dw_mysql_client_manager.session_factory
    #     async with dw_mysql_client_manager.session_factory() as session:
    #         # 执行查询SQL
    #         session:AsyncSession
    #
    #         sql = "select * from dim_customer limit 2"
    #         result = await session.execute(text(sql))
    #
    #         '''
    #         rows = result.result.all() [row对象,row对象] 当前行数据 可以.列名取值 但没有提示 一般不用
    #         rows = result.mappings().all() 列名:列值
    #         rows = result.scalars().all() [val1,val2] 第一列的值
    #         '''
    #         # 读取结果数据
    #         # 1
    #         # rows = result.all()
    #         # [('C001', '李伟', '男', '黄金'), ('C002', '王芳', '女', '白银')] <class 'sqlalchemy.engine.row.Row'>
    #         # print(rows,type(rows[0]))
    #         # for row in rows:
    #         #     for val in row:
    #         #         print(val)
    #         # print(rows[0].customer_name)
    #
    #         # 2
    #         # rows = result.mappings().all()
    #         # # [{'customer_id': 'C001', 'customer_name': '李伟', 'gender': '男', 'member_level': '黄金'},
    #         # # {'customer_id': 'C002', 'customer_name': '王芳', 'gender': '女', 'member_level': '白银'}]
    #         # # <class 'sqlalchemy.engine.row.RowMapping'>
    #         # print(rows, type(rows[0]))
    #
    #         # 3 转成python对象
    #         # ['C001', 'C002'] <class 'str'>
    #         rows = result.scalars().all()
    #         print(rows, type(rows[0]))
    #
    #         # for batch in result.scalars().yield_per(1000):
    #
    #     await dw_mysql_client_manager.close()

    # async def test_ORM():
    #     '''
    #     插入和添加
    #     :return:
    #     '''
    #     meta_mysql_client_manager.init()
    #     assert meta_mysql_client_manager.session_factory
    #     async with meta_mysql_client_manager.session_factory() as session:
    #         table_info = TableInfoMySQL(
    #             id="dim_customer",
    #             name="dim_customer",
    #             role="dim",
    #             description="客户信息表",
    #         )
    #         session.add(table_info)
    #         table_info2 = TableInfoMySQL(
    #             id="dim_customer2",
    #             name="dim_customer2",
    #             role="dim",
    #             description="客户信息表2",
    #         )
    #         table_info3 = TableInfoMySQL(
    #             id="dim_customer3",
    #             name="dim_customer3",
    #             role="dim",
    #             description="客户信息表3",
    #         )
    #         session.add_all([table_info2, table_info3])
    #         await session.commit()
    #
    #         table_info_select = await session.get(TableInfoMySQL,"dim_customer")
    #         print(table_info_select,table_info_select.id)
    #         result = await session.execute(Select(TableInfoMySQL).limit(2))
    #         print(result.all())
    #         # print(result.scalars().all())
    #
    #     await meta_mysql_client_manager.close()
    # 执行异步函数


    async def test_ORM2():
        '''
        更新删除
        :return:
        '''
        meta_mysql_client_manager.init()
        assert meta_mysql_client_manager.session_factory
        async with meta_mysql_client_manager.session_factory() as session:
            table_info = await session.get(TableInfoMySQL,"dim_customer")
            # 3更新某个值 得先查出来再更新
            # table_info.description='xxxx'
            # 4删除 得先查出来再删除
            await session.delete(table_info)
            await session.commit()
        await meta_mysql_client_manager.close()
    asyncio.run(test_ORM2())
