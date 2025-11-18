from typing import Annotated
import uuid
import csv
import json
import time

from pydantic import AfterValidator, BeforeValidator

class Utils:
    @staticmethod
    def get(inDict, path, default=None, type=None):
        out = default
        parts = path.split(".")
        cur = inDict
        success = True
        for part in parts:
            if cur and part in cur:
                cur = cur[part]
            else:
                success = False
                break
        if success:
            out = cur
        if type == 'int':
            try:
                out = int(out)
            except:
                out = default
        return out

    @staticmethod
    def guid():
        import time
        current_time = int(round(time.time() * 1000))
        guid = uuid.uuid1(node=current_time)
        guid_int = int(guid.int)
        return guid_int

    @staticmethod
    def get_time(format_str="%H:%M:%S"):
        import time
        return time.strftime(format_str)

    @staticmethod
    def _coerce_to_str(v):
        if v is None:
            raise ValueError("guid cannot be None")
        return str(v)

    @staticmethod
    def _not_empty(v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("guid cannot be empty")
        return v

# Define types
ForceStr = Annotated[str, BeforeValidator(Utils._coerce_to_str), AfterValidator(Utils._not_empty)]
