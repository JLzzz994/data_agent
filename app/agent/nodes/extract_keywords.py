import jieba.analyse
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "抽取关键字", "status": "running"})
    try:
        logger.info("开始抽取关键字")
        # 3. 业务逻辑
        # 3.1 从state中获取用户提出问题
        query = state["query"]
        # 3.2 调用结巴分词器获取关键词
        # 定义返回指定词性的元组
        allow_pos = (
            "n",  # 名词: 数据、服务器、表格
            "nr",  # 人名: 张三、李四
            "ns",  # 地名: 北京、上海
            "nt",  # 机构团体名: 政府、学校、某公司
            "nz",  # 其他专有名词: Unicode、哈希算法、诺贝尔奖
            "v",  # 动词: 运行、开发
            "vn",  # 名动词: 工作、研究
            "a",  # 形容词: 美丽、快速
            "an",  # 名形词: 难度、合法性、复杂度
            "eng",  # 英文
            "i",  # 成语
            "l",  # 常用固定短语
        )
        keywords = jieba.analyse.extract_tags(query, topK=10, allowPOS=allow_pos)
        keywords = list(set(keywords + [query]))

        # 4. 业务正常 成功
        writer({"type": "progress", "step": "抽取关键字", "status": "success"})
        logger.info(f"抽取关键字成功{keywords}")
        return {"keywords": keywords}

    except Exception as e:
        # 5. 业务异常, 错误
        writer({"type": "progress", "step": "抽取关键字", "status": "error"})
        logger.error(f"抽取关键字失败{e}")
        raise
