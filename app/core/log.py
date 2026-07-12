# 配置日志格式
import asyncio
import sys
from pathlib import Path

from loguru import logger

from app.conf.app_config import app_config
from app.core.context import get_req_id, set_req_id

log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "  # 绿色显示日志时间（精确到毫秒）
    "<level>{level: <8}</level> | "  # 按级别颜色显示日志级别（左对齐，占8个字符）
    "<magenta>request_id - {extra[request_id]}</magenta> | "  # 品红色显示request_id（从日志extra中获取）
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "  # 青色显示日志所在文件、函数、行号
    "<level>{message}</level>"  # 按级别颜色显示日志正文
)


def inject_request_id(record):
    # 获取当前请求id
    request_id = get_req_id()
    # 将request_id存入日志记录的extra字段 供日志格式中{extra[request_id]} 调用
    record["extra"]["request_id"] = request_id

# 移除loguru默认的控制台输出(避免重复输出日志)
logger.remove()
# 给日志打补丁 使其在输出每条日志前执行inject_request_id函数,注入request_id
logger = logger.patch(inject_request_id)

# 如果配置中开启了控制台日志输出
if app_config.logging.console.enable:
    #添加控制台日志输出器
    logger.add(sink=sys.stdout,level=app_config.logging.console.level,format=log_format)

if app_config.logging.file.enable:
    # 解析日志文件存储路径
    path = Path(app_config.logging.file.path)
    path.mkdir(parents=True,exist_ok=True)
    logger.add(
        sink=path/"app.log",
        level=app_config.logging.file.level,
        format=log_format,
        rotation=app_config.logging.file.rotation,
        retention=app_config.logging.file.retention, # 保留时长
        encoding="utf-8"
    )

if __name__ == '__main__':
    async def req1():
        # 接收到请求
        set_req_id(1111)
        # 模拟处理
        await asyncio.sleep(1)
        logger.info(get_req_id())


    async def req2():
        # 接收到请求
        set_req_id(2222)
        # 模拟处理
        await asyncio.sleep(1)
        logger.info(get_req_id())


    async def test():
        await asyncio.gather(req1(), req2())

    asyncio.run(test())