import uuid
import csv
import json
import time
import os


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
    def getFilesByExtension(filePath, allowedExtensions):
        foundFiles = []
        for fileName in os.listdir(filePath):
            fileExtension = os.path.splitext(fileName)[1][1:]  # remove the dot from the extension
            if fileExtension.lower() in allowedExtensions:
                foundFiles.append(fileName)
        return foundFiles

