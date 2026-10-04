"""Helpers for turning Mongo documents into API-safe dicts."""
from datetime import datetime, timezone
from typing import Any


def _convert(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, dict):
        return {k: _convert(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_convert(x) for x in v]
    return v


def to_api(doc):
    """Drop Mongo's ObjectId (_id) and mark stored naive-UTC datetimes as UTC."""
    if doc is None:
        return None
    return {k: _convert(v) for k, v in doc.items() if k != "_id"}
