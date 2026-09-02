from dataclasses import dataclass


@dataclass(frozen=True)
class AccessScope:
    """从可信认证网关下发的数据访问范围。"""

    tenant_id: str
    allowed_shop_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.tenant_id.strip():
            raise ValueError("tenant_id 不能为空")
