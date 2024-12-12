import requests
import json
import os
import time
import dotenv
import random
from constants import *

#num_tokens
tiktoken = None
try:
    import tiktoken
except:
    print("Tiktoken not installed")

from Utils import Utils
from HuggingFaceLib import HuggingFaceLib

pq = None
try:
    import pyarrow.parquet as pq
except:
    print("pyarrow not installed")

class TestReserveLib():
    test_scale_mode = True
    words = None
    #host = "https://api.example.com"
    #host = 'http://localhost:8000'
    host = None
    default_host = "http://localhost:5002"

    def __init__(self):
        if not self.host:
            dotenv.load_dotenv()
            host = os.getenv('HOST')
            if not host:
                host = self.default_host
        self.host = host

    def getPage(self, url):
        #print("GET", url)
        if self.test_scale_mode:
            print(f"{YELLOW}Returning simulated task window{COLOR_END}")
            f = open("example_task_window.json")
            body = f.read()
            f.close()
            json_data = json.loads(body)
            json_data['data']['task']['id'] = random.randint(11111111, 99999999)
            print(json_data)
            return json_data

        response = requests.get(url)

        if response.status_code == 200:
            json_data = response.json()
            f = open("example_task_window.json", "w")
            f.write(json.dumps(json_data))
            f.close()
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

    def get_rows2(self, file_path, begin_row, end_row):
        rows = []
        with open(file_path, 'r') as file:
            for i, line in enumerate(file, start=1):
                if begin_row <= i <= end_row:
                    if line:
                        rows.append(line.rstrip())
                url = self.host+"/endpoint"
        return rows
    def post(self, url, data):
        response = requests.post(url, json=data)
        if response.status_code == 200:
            #print("RESPONSE", response.content, dir(response))
            return response.json()
        else:
            print("ERROR", response.status_code, response)

    def process(self, taskId=None):
        baseUrl = self.host
        url = baseUrl + '/cgp/api/v1/reserve_task'
        if taskId:
            url += f"?taskId={taskId}"
        task = self.getPage(url)
        success = Utils.get(task, 'success')
        if success:
            encoding = None
            if tiktoken:
                #encoding = tiktoken.encoding_for_model("gpt-4o-mini")
                encoding = tiktoken.get_encoding("cl100k_base")


            taskData = Utils.get(task, 'data.task')
            taskId = Utils.get(taskData, 'id')
            dataUrl = Utils.get(task, 'data.task.data_url')
            #print(json.dumps(task))
            #return
            if not dataUrl:
                print(f"Invalid data URL: {dataUrl} for task {taskId}. Aborting.")
                return
            prompts = Utils.get(task, 'data.prompts')

            # Check if this is a HuggingFace url
            if dataUrl.find("|") != -1:
                cacheName = Utils.md5(dataUrl)
                (dataSetId, filename) = dataUrl.split('|')
                basePath = os.path.join("cache", cacheName)
                cachePath = os.path.join(basePath, filename)
                print("filename", filename)
                print("cacheName", cacheName)
                print("basePath", basePath)
                print("cachePath", cachePath)
                print(f"Huggingface ds: {dataSetId} file: {filename}")
                if not os.path.isfile(cachePath):
                    print(f"Not cached. Download HF file to {cachePath}")
                    hfl = HuggingFaceLib()
                    hfl.downloadFile(dataSetId, filename, path=basePath)
                else:
                    print(f"Found cache file: {cachePath}")
                try:
                    parquet_file = pq.ParquetFile(cachePath)
                except Exception as e:
                    print("ERROR", e)
                    return
                total_rows = parquet_file.metadata.num_rows
                print("Total number of rows:", total_rows)

                for row_group in range(parquet_file.num_row_groups):
                    print("row_group", row_group, taskData)
                    table = parquet_file.read_row_group(row_group) #, columns=['column1', 'column2'])
                    #print("table", table)
                    validRows = 0
                    #begin_row = random.randint(2, 50) #Utils.get(taskData, 'data.begin_row')
                    #end_row = begin_row+20 # Utils.get(taskData, 'data.end_row')
                    begin_row = Utils._int(Utils.get(taskData, 'begin_row'))
                    end_row = Utils._int(Utils.get(taskData, 'end_row'))
                    print(f"{YELLOW}Processing rows {begin_row} - {end_row}{COLOR_END}")
                    num_rows_in_group = table.num_rows
                    rows = []
                    for i in range(num_rows_in_group):
                        if i >= begin_row:
                            row = table.slice(i, 1)
                            rows.append(json.dumps(row.to_pydict()))
                        if i > end_row:
                            break
                    #print(rows)
                    if False:
                        num_rows_in_group = table.num_rows
                        for i in range(num_rows_in_group):
                            row = table.slice(i, 1)
                            #print("ROW", i, row, dir(row))
                            print(row.to_pydict())
                            if i>2:
                                break


                #return
            else:
                cacheName = Utils.md5(dataUrl)+".dat"
                cachePath = os.path.join("cache", cacheName)
                if not os.path.isfile(cachePath):
                    print("Download file")
                    fullUrl = self.host + dataUrl
                    self.getFile(fullUrl, cachePath)
                else:
                    print(f"Found cache for task {taskId} at {cachePath}")
                begin_row = random.randint(2, 50) #Utils.get(taskData, 'data.begin_row')
                end_row = begin_row+10 # Utils.get(taskData, 'data.end_row')
                print("taskData", taskData)
                rows = []
                if False:
                    for idx, row in enumerate(self.get_rows(cachePath, begin_row, end_row)):
                        rows.append(row)
                else:
                    rows = self.get_rows2(cachePath, begin_row, end_row)
            #print("ROWS", rows)
            inferenceApi = "http://api.infer.com:8001/api/v1/ai"
            inferenceApi = "http://localhost:5002/cgp/api/v1/infer"
            outVarDict = {'data':"\n".join(rows)}
            if not prompts or len(prompts) == 0:
                print(f"{RED}No prompts for task {taskId}. Aborting.{COLOR_END}")
                return False

            #print(prompts)
            #return

            # Run through Prompt Chain
            totalTokens = 0
            for idx, promptRow in enumerate(prompts):
                promptSend = Utils.get(promptRow, 'prompt')
                for key,val in outVarDict.items():
                    promptSend = promptSend.replace(f"{key}", val)
                promptAbbr = promptSend[0:255].replace('\n','')
                print(f"Processing prompt {idx} Prompt: {promptAbbr}...")
                outVar = Utils.get(promptRow, 'output_variable_name')
                a = {
                    "body":promptSend,
                }
                if encoding:
                    num_tokens = len(encoding.encode(promptSend))
                    totalTokens += num_tokens

                #continue
                if not self.test_scale_mode:
                    response = self.post(inferenceApi, a)
                else:
                    wait = 5
                    print(f"{YELLOW}Simulate OpenAI inference call for {wait} seconds...{COLOR_END}")
                    time.sleep(wait)
                    response = {'data':self.generate_random_sentence()}
                if outVar:
                    outVarDict[outVar] = response['data']
            postUrl = baseUrl + f"/cgp/api/v1/task/{taskId}/results"
            outVarDict['totalTokens'] = totalTokens
            print(f"POST results for task id: {GREEN}{taskId}{COLOR_END} to {postUrl} -- {outVarDict}")
            if not self.test_scale_mode:
                self.post(postUrl, outVarDict)
            else:
                waitPost = 1
                print(f"{YELLOW}Simulate post results for {waitPost} seconds...{COLOR_END}")
            return True
        else:
            print(f"{YELLOW}No tasks available{COLOR_END}")
            return False
            #break
    def generate_random_sentence(self):
        if not self.words:
            f = open('words.json')
            body = f.read()
            f.close()
            self.words = json.loads(body)
        noun1 = random.choice(self.words['nouns'])
        verb = random.choice(self.words['verbs'])
        adjective1 = random.choice(self.words['adjectives'])
        noun2 = random.choice(self.words['nouns'])
        preposition = random.choice(self.words['prepositions'])
        article1 = random.choice(self.words['articles'])
        article2 = random.choice(self.words['articles'])

        sentence_structures = [
            f"The {article1} {adjective1} {noun1} {verb}s {article2} {noun2}.",
            f"The {article1} {noun1} {verb}s {preposition} the {article2} {adjective1} {noun2}.",
            f"The {article1} {adjective1} {noun1} {verb}ed the {article2} {noun2}.",
        ]

        sentence = random.choice(sentence_structures)
        return sentence

if True and __name__ == "__main__":
    trl = TestReserveLib()
    allowNegativeBalance = True
    action = "server"
    #action = "single"
    if action == "server":
        while True:
            success = trl.process()
            if success:
                time.sleep(1)
            else:
                time.sleep(5)
    elif action == "single":
        taskId = 2148
        print(f"Processing task {taskId}..")
        success = trl.process(taskId=taskId)

if False and __name__ == "__main__":
    trl = TestReserveLib()
    random_sentences = [trl.generate_random_sentence() for _ in range(20)]
    print(random_sentences)

