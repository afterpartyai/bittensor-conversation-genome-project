from typing_extensions import Annotated
from pydantic import BeforeValidator, AfterValidator

def _coerce_to_str(v):
    if v is None:
        raise ValueError("guid cannot be None")
    return str(v)

def _not_empty(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("guid cannot be empty")
    return v

ForceStr = Annotated[str, BeforeValidator(_coerce_to_str), AfterValidator(_not_empty)]