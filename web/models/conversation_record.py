from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class Participant(BaseModel):
    idx: int
    guid: int
    title: str


class ConversationData(BaseModel):
    id: str
    guid: int
    topic: str
    lines: List[List[Any]]
    participants: Dict[str, Participant]


class ConversationRecord(BaseModel):
    id: int
    source_id: int
    guid: str
    idx: int
    topic: str
    data: ConversationData
    created_at: datetime
    updated_at: datetime

