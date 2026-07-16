from pathlib import Path

from dataclasses import dataclass

from app.conf.load_config import load_config


# ==================== 日志配置模型 ====================

@dataclass
class Console:
    enable: bool
    level: str


@dataclass
class File:
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class LoggingConfig:
    file: File
    console: Console


# ==================== database配置模型 ====================

@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


# ==================== Qdrant 配置模型 ====================

@dataclass
class QdrantConfig:
    host: str
    port: int
    embedding_size: int


# ==================== Embedding 配置模型 ====================

@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str


# ==================== ES 配置模型 ====================

@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


# ==================== LLM 配置模型 ====================

@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url:str
    model_provider:str

# ==================== 应用总配置模型 ====================

@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig


# 配置文件路径
_yaml_path = Path(__file__).parents[2] / "conf" / "app_config.yaml"

app_config: AppConfig = load_config(_yaml_path, AppConfig)

if __name__ == '__main__':
    # print(app_config)
    print(app_config.logging.console.level)
