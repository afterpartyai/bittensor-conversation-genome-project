import uuid
import csv
import json
import time
import os
import binascii
import uuid
import requests
import re


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

    @staticmethod
    def readFile(filePath):
        try:
            with open(filePath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"The file {filePath} was not found.")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    @staticmethod
    def writeFile(filePath, body):
        with open(filePath, 'w', encoding='utf-8') as outputFile:
            outputFile.write(body)
        
    @staticmethod
    def isAlphaNumeric(input_string):
        alphanumeric_count = 0
        
        for char in input_string:
            if char.isalnum():
                alphanumeric_count += 1
        
        return alphanumeric_count >= 4

    @staticmethod
    def getUuid():
        return str(uuid.uuid4())


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
    def getUrl(url, headers=None, verbose=False, noJson=False):
        out = {"success":False, "code":-1, "errors":[]}
        if not requests:
            print("No requests library")

            return out

        try:
            response = requests.get(url, params=None, cookies=None, headers=headers)
            out["code"] = response.status_code
            if out["code"] == 200:
                out["body"] = response.text
                if not noJson:
                    try:
                        out["json"] = response.json()
                    except Exception as e:
                        msg = f"getUrl error processing JSON: {e}"
                        print(msg)
                        out['errors'].append({"id":19839121, "msg":msg})
            else:
                out['errors'].append({"id":198390129, "msg":response.text})
        except Exception as e:
            out['errors'].append({"id":198390128, "msg":f"API ERROR: {e}"})


        return out

    @staticmethod
    def collapseRepeatChars(input_string):
        """Collapse multiple newline characters into a single newline."""
        return re.sub(r'\n+', '\n', input_string)
        
    @staticmethod
    def postUrl(url, postData=None, jsonData=None, headers=None, cert=None, key=None, verbose=False, returnText=True):
        out = {"success":False, "body":None, "json": None, "code":-1, "errors":[]}
        if not requests:
            msg = "No requests library in Utils"
            print(msg)
            out['errors'].append({"id":142674, "msg":msg})
            return out
        if not headers:
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en_US",
            }

        try:
            response = requests.post(url, headers=headers, json=jsonData, data=postData, cert=cert)
            if verbose:
                print(response.text)
            if False:
                print("HEADERS", response.headers)
            out["code"] = response.status_code
            out["headers"] = response.headers
            if out["code"] == 200:
                out["success"] = True
                if returnText:
                    out["body"] = response.text
                else:
                    out["body"] = response.content
                try:
                    out["json"] = response.json()
                except:
                    pass
            else:
                out['errors'].append({"id":19839009, "msg":response.text})
        except Exception as e:
            out['errors'].append({"id":19839010, "msg":e})


        return out

