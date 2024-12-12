import time
import json
import requests
import os
import re
from constants import *

dotenv = None
try:
    import dotenv
except:
    print("dotenv not installed")


HfApi = hf_hub_download = None
try:
    from huggingface_hub import HfApi, hf_hub_download
except:
    print("huggingface_hub not installed")


class HuggingFaceLib():
    apiKey = None
    keyPath = ".hf_key"

    def __init__(self, apiKey = None):
        if not apiKey and dotenv:
            dotenv.load_dotenv()
            apiKey = os.getenv('HUGGINGFACE_API_KEY')
        elif not dotenv and os.path.isfile(self.keyPath):
            print(f"{CYAN}Loading HF key from file{COLOR_END}")
            f = open(self.keyPath)
            apiKey = f.read()
            f.close()
            apiKey = apiKey.strip()
            print(apiKey)
        self.apiKey = apiKey


    def getDatasetInfo(self, dataset_id = "dataverse-scraping/reddit_dataset_71", forceUpdate=False):
        cl = CacheLib()
        key = f"huggingface_dataset_{dataset_id}"
        out = None
        if not forceUpdate:
            out = cl.get(key)
            if out:
                return out
        print("MISS")
        out = {"success": 0, "id":None, "tags":[], "num_files":0, "files":[], "exts":{}, "errors":[]}

        api = HfApi(token=self.apiKey)

        try:
            dataset_info = api.dataset_info(dataset_id)
        except Exception as e:
            out['errors'].append([6374745, str(e).replace("\n", " ")])
            return out
        out['id'] = dataset_info.id
        out['tags'] = dataset_info.tags
        out['success'] = 1
        #print("ID", dataset_info.id)
        #print("TAGS", dataset_info.tags)
        #print("SIBS", len(dataset_info.siblings))
        #for attr in dir(dataset_info):
        #    print(attr, get_attr(dataset_info, attr))
        fileExts = {}
        files = []
        skipExts = ['md']
        labelColors = {
            "PAR" : "green",
            "CSV" : "blue",
        }
        numFiles = 0
        for sibling in dataset_info.siblings:
            if sibling.rfilename:
                if sibling.rfilename[0:1] == '.':
                    continue
                parts = sibling.rfilename.split('.')
                fileExt = parts[len(parts)-1]
                if fileExt in skipExts:
                    continue
                if len(parts)>1:
                    if not fileExt in fileExts:
                        fileExts[fileExt] = 0
                    fileExts[fileExt] += 1
                    crc = abs(Utils.dictToCrc(dataset_id + "|" + sibling.rfilename))
                    extLabel = fileExt[0:3].upper()
                    files.append({"crc":crc, "name":sibling.rfilename, "ext":fileExt, "ext_label":extLabel})
                    numFiles += 1
                #print("sibling", sibling)
        out['exts'] = fileExts
        out['files'] = files
        out['num_files'] = numFiles
        # Cache for 1 hour
        cl.put(key, out, lifeSeconds=60*60)
        return out

        print("Available Formats:", dataset_info.cardData.get('formats', []))
        print("Dataset Size:", dataset_info.cardData.get('size', 'Unknown'))

        # To get files and versions, check the card data if available
        files = dataset_info.siblings
        for file in files:
            print(f"File: {file.rfilename}, Size: {file.size}, Revision: {file.revision}")

    def downloadFile(self, dataset_id, filename, path, forceUpdate=False):
        api = HfApi(token=self.apiKey)
        try:
            file_path = hf_hub_download(repo_id=dataset_id, filename=filename, local_dir=path, repo_type="dataset", token=self.apiKey)
            print(f"Downloaded file path: {file_path}")
        except Exception as e:
            print(f"Error downloading file: {e}")

