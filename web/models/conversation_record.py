from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel

from conversationgenome.utils.types import ForceStr


class Participant(BaseModel):
    idx: ForceStr
    guid: ForceStr
    title: str


class ConversationData(BaseModel):
    id: ForceStr
    guid: ForceStr
    lines: List[List[Any]]
    participants: Dict[str, Participant]


class ConversationRecord(BaseModel):
    id: ForceStr
    source_id: ForceStr
    guid: ForceStr
    idx: int
    data: ConversationData
    created_at: datetime
    updated_at: datetime
