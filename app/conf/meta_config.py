from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.conf.load_config import load_config


# ==================== 字段信息配置模型 ====================
@dataclass
class ColumnConfig:
    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool


# ==================== 表信息配置模型 ====================
@dataclass
class TableConfig:
    name: str
    role: str
    description: str
    columns: list[ColumnConfig]


# ==================== 指标信息配置模型 ====================
@dataclass
class MetricConfig:
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


# ==================== 元数据的总配置模型 ====================
@dataclass
class MetaConfig:
    tables: Optional[list[TableConfig]] = None
    metrics: Optional[list[MetricConfig]] = None


# 得到yaml配置文件的绝对路径
_yaml_path = Path(__file__).parents[2] / "conf/meta_config.yaml"

meta_config: MetaConfig = load_config(_yaml_path, MetaConfig)

if __name__ == "__main__":
    print(meta_config)
    print(meta_config.metrics[0].description)
