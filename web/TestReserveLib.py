import requests
import json
import os
import time

import dotenv

from Utils import Utils

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

    def get_rows(self, file_path, begin_row, end_row):
        with open(file_path, 'r') as file:
            for i, line in enumerate(file, start=1):
                if begin_row <= i <= end_row:
                    yield line.rstrip()

                url = "https://api.example.com/endpoint"
    def post(self, url, data):
        response = requests.post(url, json=data)
        if response.status_code == 200:
            #print("RESPONSE", response.content, dir(response))
            return response.json()
        else:
            print("ERROR", response.status_code, response)

    def process(self):
        baseUrl = 'http://localhost:8001'
        url = baseUrl + '/api/v1/reserve_task'
        task = self.getPage(url)
        success = Utils.get(task, 'success')
        if success:
            taskData = Utils.get(task, 'data.task')
            taskId = Utils.get(taskData, 'id')
            dataUrl = Utils.get(task, 'data.task.data_url')
            if not dataUrl:
                print(f"Invalid data URL: {dataUrl} for task {taskId}. Aborting.")
                return
            prompts = Utils.get(task, 'data.prompts')
            cacheName = Utils.md5(dataUrl)+".dat"
            cachePath = os.path.join("cache", cacheName)
            if not os.path.isfile(cachePath):
                print("Download file")
                self.getFile(dataUrl, cachePath)
            else:
                print("Found cache")
            begin_row = 2
            end_row = 5
            rows = []
            for idx, row in enumerate(self.get_rows(cachePath, begin_row, end_row)):
                rows.append(row)

            inferenceApi = "http://api.infer.com:8001/api/v1/ai"
            outVarDict = {'data':"\n".join(rows)}
            for promptRow in prompts:
                promptSend = Utils.get(promptRow, 'prompt')
                for key,val in outVarDict.items():
                    promptSend = promptSend.replace(f"{key}", val)
                outVar = Utils.get(promptRow, 'output_variable_name')
                a = {
                    "body":promptSend,
                }
                response = self.post(inferenceApi, a)
                if outVar:
                    outVarDict[outVar] = response['data']
            postUrl = baseUrl + f"/api/v1/task/{taskId}/results"
            print("POST", postUrl, outVarDict)
            self.post(postUrl, outVarDict)
            return True
        else:
            print("No tasks available")
            return False
            #break


if __name__ == "__main__":
    trl = TestReserveLib()
    while True:
        success = trl.process()
        if success:
            time.sleep(1)
        else:
            time.sleep(5)


