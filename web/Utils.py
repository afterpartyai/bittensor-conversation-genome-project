import uuid
import csv
import json
import time
import hashlib

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

    def md5(inStr):
        md5_hash = hashlib.md5()
        md5_hash.update(inStr.encode('utf-8'))
        return md5_hash.hexdigest()
