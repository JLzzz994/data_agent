import asyncio
from _contextvars import ContextVar

# 创建一个用来存储请求id的contextvar对象
_req_request_id = ContextVar("req_id", default="")


# 保存请求Id
def set_req_id(request_id: str):
    return _req_request_id.set(request_id)


# 获取请求Id
def get_req_id() -> str:
    return _req_request_id.get()

if __name__ == '__main__':
    async def req1():
        print(f"请求1开始准备执行,req_id={get_req_id()}")
        set_req_id("111")
        print(f"请求1执行完毕: req_id={get_req_id()}")

    async def req2():
        print(f"请求2开始准备执行,req_id={get_req_id()}")
        set_req_id("222")
        print(f"请求2执行完毕: req_id={get_req_id()}")

    def test2():
        print(f"------{get_req_id()}")
        set_req_id("333")
        print(f"------{get_req_id()}")
        set_req_id("444")
        print(f"------{get_req_id()}")

    async def test():
        cor1 = req1()
        cor2 = req2()
        await asyncio.gather(cor1,cor2)
    # test2()
    asyncio.run(test())