import random
from datetime import datetime, timezone

from conversationgenome.utils.Utils import Utils

class logging:
    time_format = '%Y-%m-%d %H:%M:%S'
    def debug(*args, **kwargs):
        now = datetime.now(timezone.utc)
        print(now.strftime(logging.time_format), "DEBUG", " | ", *args[1:], sep="  ")
    def info(*args, **kwargs):
        now = datetime.now(timezone.utc)
        print(now.strftime(logging.time_format), "INFO", " | ", *args[1:], sep="  ")
    def error(*args, **kwargs):
        now = datetime.now(timezone.utc)
        print(now.strftime(logging.time_format), "ERROR", " | ", *args[1:], sep="  ")

class MockBt:
    def __init__(self):
        self.logging = logging()

    def getUids(self, num=10, useFullGuids=False):
        uids = []
        for i in range(num):
            # useGuids is more realistic, but harder to read in testing
            if useFullGuids:
                uids.append(Utils.guid())
            else:
                uids.append(random.randint(1000, 9999))

        return uids
