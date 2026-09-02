from dataclasses import dataclass
from pathlib import Path

from app.conf.load_config import load_config


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


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class MilvusConfig:
    host: str
    port: int
    token: str
    embedding_size: int


@dataclass
class EmbeddingConfig:
    host: str
    port: int
    model: str


@dataclass
class ESConfig:
    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    model_name: str
    api_key: str
    base_url: str
    model_provider: str


@dataclass
class AppConfig:
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    milvus: MilvusConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig


_yaml_path = Path(__file__).parents[2] / "conf" / "app_config.yaml"
app_config: AppConfig = load_config(_yaml_path, AppConfig)
