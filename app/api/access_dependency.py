import hmac
import os
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.security.access_scope import AccessScope


async def get_access_scope(
    tenant_id: Annotated[str | None, Header(alias="X-Internal-Tenant-Id")] = None,
    shop_ids: Annotated[str | None, Header(alias="X-Internal-Shop-Ids")] = None,
    gateway_token: Annotated[str | None, Header(alias="X-Internal-Gateway-Token")] = None,
) -> AccessScope:
    """仅接受可信网关注入的内部权限头；缺省时拒绝访问。"""
    expected_token = os.getenv("INTERNAL_GATEWAY_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INTERNAL_GATEWAY_TOKEN 未配置",
        )
    if not gateway_token or not hmac.compare_digest(gateway_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的内部认证上下文",
        )
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="缺少租户数据权限",
        )

    allowed_shop_ids = tuple(
        item.strip() for item in (shop_ids or "").split(",") if item.strip()
    )
    return AccessScope(tenant_id=tenant_id.strip(), allowed_shop_ids=allowed_shop_ids)
