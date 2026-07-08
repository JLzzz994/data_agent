import asyncio
from typing import Optional

from sqlalchemy import text, Select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.testing import rowset

from app.conf.app_config import DBConfig, app_config
from app.models.mysql.table_info_mysql import TableInfoMySQL


class MySQLClientManager:
    def __init__(self, config: DBConfig):
        self.config = config
        self.client: Optional[AsyncEngine] = None
        self.session_factory:Optional[async_sessionmaker] = None
    def url(self):
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}/{self.config.database}?charset=utf8mb4"

    def init(self):
        self.client = create_async_engine(self.url())
        self.session_factory = async_sessionmaker(self.client,autoflush=False,autobegin=True)
    async def close(self):
        await self.client.dispose()


dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)

if __name__ == '__main__':
    # 1 sqlalchemy sql 方式
    async def test():
        # 1 初始化客户端
        dw_mysql_client_manager.init()
        # 2 创建异步会话
        async with AsyncSession(dw_mysql_client_manager.client, autoflush=False, autobegin=True) as session:
            sql = "select * from dim_customer limit 2"
            # <sqlalchemy.engine.cursor.CursorResult object at 0x0000022EEB4DD9B0>
            result = await session.execute(text(sql))
            """
            result.all(): 包含n个row对象的数组， row对象可以通过for来遍历包含字段值
            result.mappings().all(): 包含n个rowMapping对象的数组， rowMapping对象可以通过for来遍历出字段名和字段值
            result.scalars().all(): 包含n个第一个字段值的数组
            """
            # 3 读取结果
            # 3.1
            # rows = result.all()
            # # #[('C001', '李伟', '男', '黄金'), ('C002', '王芳', '女', '白银')] <class 'sqlalchemy.engine.row.Row'>
            # # print(rows,type(rows[0]))
            # #('C001', '李伟', '男', '黄金')
            # # ('C002', '王芳', '女', '白银')
            # for row in rows:
            #     print(row)
            # 3.2 RowMapping
            # rows = result.mappings().all()
            # #[{'customer_id': 'C001', 'customer_name': '李伟', 'gender': '男', 'member_level': '黄金'},
            # # {'customer_id': 'C002', 'customer_name': '王芳', 'gender': '女', 'member_level': '白银'}]
            # #<class 'sqlalchemy.engine.row.RowMapping'>
            # print(rows,type(rows[0]))
            # for row in rows:
            #     print(row)
            # 3.3
            # first_columns = result.scalars().all()
            # #['C001', 'C002'] <class 'str'>
            # # print(first_columns,type(first_columns[0]))
            # for first_column in first_columns:
            #     print(first_column)
        await dw_mysql_client_manager.close()


    # 2 ORM
    # 添加和查询
    async def test_ORM1():
        # 初始化客户端
        meta_mysql_client_manager.init()
        async with meta_mysql_client_manager.session_factory() as session:
            session: AsyncSession
            table1_info = TableInfoMySQL(
                id="dim_customer1",
                name="dim_customer1",
                role="dim",
                description="客户信息表1"
            )
            # 2.1 添加单条数据
            session.add(table1_info)
            # 2.1.1这里是查看代码中对象在内存中的数据
            # print(table1_info.name)
            table2_info = TableInfoMySQL(
                id="dim_customer2",
                name="dim_customer2",
                role="dim",
                description="客户信息表2"
            )
            table3_info = TableInfoMySQL(
                id="dim_customer3",
                name="dim_customer3",
                role="dim",
                description="客户信息表3"
            )
            # 2.2 添加多条数据
            session.add_all([table2_info, table3_info])
            await session.commit()

            # 2.3 查询 查询一条数据
            # table_info_select = await session.get(TableInfoMySQL,"dim_customer1")
            # print("table_info1:",table_info_select.name,table_info_select.description)
            # 2.4 查询多条数据
            table_info_select2 = await session.execute(Select(TableInfoMySQL).limit(2))
            #[(<app.models.mysql.table_info_mysql.TableInfoMySQL object at 0x000001D90BB72960>,),
            # (<app.models.mysql.table_info_mysql.TableInfoMySQL object at 0x000001D90BA8D610>,)]
            # print(table_info_select2.all())
            #[<app.models.mysql.table_info_mysql.TableInfoMySQL object at 0x0000022942D46390>,
            # <app.models.mysql.table_info_mysql.TableInfoMySQL object at 0x0000022942E250D0>]
            # 去掉列表中的单个对象带的元组符号
            table_infos:list[TableInfoMySQL] = table_info_select2.scalars().all()
            print()
        await meta_mysql_client_manager.close()
    # 3 更新和删除
    async def test_ORM2():
        meta_mysql_client_manager.init()
        async with meta_mysql_client_manager.session_factory() as session:
            session: AsyncSession
            table_info = await session.get(TableInfoMySQL, "dim_customer1")
            # 3.1 更新
            # table_info.description="0.0"

            # 3.2 删除
            await session.delete(table_info)
            await session.commit()
        await meta_mysql_client_manager.close()

    asyncio.run(test_ORM2())
