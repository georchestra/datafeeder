from pydantic import BaseModel


class GroupItem(BaseModel):
    id: str
    label: str
