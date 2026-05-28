import re
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel


class GroupItem(BaseModel):
    id: str
    label: str


def filter_console_items(items: list[dict[str, Any]], regex: str) -> list[dict[str, Any]]:
    if not regex:
        return items

    try:
        pattern = re.compile(regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex {regex}: {e}")

    result: list[dict[str, Any]] = []
    for item in items:
        name = item.get("name")
        if not name:
            continue
        match = pattern.search(name)
        if not match:
            continue

        item["name"] = match.group(1) if match.lastindex else name
        result.append(item)

    return result
