from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel


class ConversationMetadata(BaseModel):
    tags: List[str]
    vectors: Dict[str, Dict[str, List[float]]]
    participantProfiles: Optional[List[str]] = None
