import uuid
import csv
import json
import time
import hashlib
import binascii

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
    def guid(returnInt=True):
        import time
        current_time = int(round(time.time() * 1000))
        guid = uuid.uuid1()
        if returnInt:
            guid_int = int(guid.int)
            return guid_int
        else:
            return guid

    @staticmethod
    def get_time(format_str="%H:%M:%S"):
        import time
        return time.strftime(format_str)

    @staticmethod
    def md5(inStr):
        md5_hash = hashlib.md5()
        md5_hash.update(inStr.encode('utf-8'))
        return md5_hash.hexdigest()

    @staticmethod
    def dictToCrc(data=None):
        if data == None:
            data = Utils.getUuid()
            #print("UUID", data)
        try:
            dataStr = str(json.dumps(data))
            crc = binascii.crc32(dataStr.encode('utf8'))
            return crc
        except:
            print("Error converting dictToCrc", data)

    @staticmethod
    def empty(val):
        out = True
        #print("TYPE", type(val))
        valType = type(val)
        if not val:
            out = True
        elif valType == str:
            if len(val.strip()) > 0:
                out = False
        elif valType == int:
            if val != 0:
                out = False
        elif valType == list:
            #print("LIST", val)
            if len(val) != 0:
                out = False
        elif valType == dict:
            #print("DICT", val)
            if len(val.keys()) != 0:
                out = False
        else:
            print("EMPTY doesn't work with type %s" % (valType))
        return out

    @staticmethod
    def _int(val, default=None):
        out = default
        try:
            out = int(val)
        except:
            pass
        return out
