import requests
import json
from Utils import Utils
import os

class TestReserveLib():
    def getPage(self, url):
        response = requests.get(url)

        if response.status_code == 200:
            json_data = response.json()
            return json_data
        else:
            print(f"Failed to retrieve JSON: {response.status_code}")

    def getFile(self, url, outPath):
        response = requests.get(url, stream=True)

        if response.status_code == 200:
            with open(outPath, 'wb') as f:
                while True:
                    chunk = response.raw.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
            print(f"File downloaded: {outPath}")
        else:
            print(f"Failed to download file: {response.status_code}")


if __name__ == "__main__":
    trl = TestReserveLib()
    url = 'http://localhost:8001/api/v1/reserve_task'
    task = trl.getPage(url)
    dataUrl = Utils.get(task, 'data.task.data_url')
    cacheName = Utils.md5(dataUrl)+".dat"
    cachePath = os.path.join("cache", cacheName)
    if not os.path.isfile(cachePath):
        print("Download file")
        trl.getFile(dataUrl, cachePath)
    else:
        print("Found cache")
    print()


