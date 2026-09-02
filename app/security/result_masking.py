"""查询结果统一脱敏。"""
from collections.abc import Mapping

PHONE_KEYS = {"mobile", "phone", "receiver_mobile", "buyer_mobile", "contact_phone"}
EMAIL_KEYS = {"email", "buyer_email", "receiver_email"}
NAME_KEYS = {"receiver_name", "buyer_name", "buyer_nick", "contact_name"}
ADDRESS_KEYS = {"address", "receiver_address", "detail_address"}


def _mask_phone(value: str) -> str:
    if len(value) < 7:
        return "***"
    return f"{value[:3]}****{value[-4:]}"


def _mask_email(value: str) -> str:
    if "@" not in value:
        return "***"
    name, domain = value.split("@", 1)
    return f"{name[:1]}***@{domain}"


def _mask_name(value: str) -> str:
    return f"{value[:1]}**" if value else value


def _mask_address(value: str) -> str:
    return f"{value[:6]}****" if len(value) > 6 else "***"


def mask_row(row: Mapping) -> dict:
    masked = dict(row)
    for key, value in list(masked.items()):
        if value is None:
            continue
        normalized = str(key).lower()
        text_value = str(value)
        if normalized in PHONE_KEYS:
            masked[key] = _mask_phone(text_value)
        elif normalized in EMAIL_KEYS:
            masked[key] = _mask_email(text_value)
        elif normalized in NAME_KEYS:
            masked[key] = _mask_name(text_value)
        elif normalized in ADDRESS_KEYS:
            masked[key] = _mask_address(text_value)
    return masked


def mask_rows(rows: list[Mapping]) -> list[dict]:
    return [mask_row(row) for row in rows]
