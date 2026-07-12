from pathlib import Path
from typing import TypeVar, Type

from omegaconf import OmegaConf

T = TypeVar("T")


def load_config(config_file: Path, schema_cls: Type[T]) -> T:
    # 根据路径加载配置文件数据 =》DictConfig对象
    _yaml_data = OmegaConf.load(config_file)

    # 将数据转换为MetaConfig类型的对象
    config: T = OmegaConf.to_object(OmegaConf.merge(schema_cls, _yaml_data))
    return config
