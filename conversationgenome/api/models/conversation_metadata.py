from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel


class ConversationMetadata(BaseModel):
    tags: List[str]
    vectors: Dict[str, Dict[str, List[float]]]
    participantProfiles: Optional[List[str]] = None

class ConversationQualityMetadata(BaseModel):
    quality_score: int
    primary_reason: Optional[str] = None
    reason_details: Optional[str] = None
