from typing import Dict, List, Optional

from pydantic import BaseModel


class RawMetadata(BaseModel):
    tags: List[str]
    success: bool
    vectors: Optional[Dict[str, Dict[str, List[float]]]]