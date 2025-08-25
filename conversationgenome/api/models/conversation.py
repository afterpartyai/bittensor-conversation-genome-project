from typing import Annotated, List, Optional, Tuple

from pydantic import BaseModel

from conversationgenome.api.models.conversation_metadata import ConversationMetadata


class Conversation(BaseModel):
    guid: Annotated[str, ...]
    lines: List[Tuple[int, str]]
    miner_task_prompt: Optional[str] = None
    participants: Optional[List[str]] = None
    min_convo_windows: Optional[int] = None
    indexed_windows: Optional[List[Tuple[int, List[str]]]] = None
    windows: Optional[List[List[str]]] = None
    metadata: Optional[ConversationMetadata] = None 