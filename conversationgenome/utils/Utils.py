import os
import random
import re
import time
import uuid

import numpy as np
import requests

from conversationgenome.api.models.conversation import Conversation


class Utils:
    @staticmethod
    def get(inDict, path, default=None, dataType=None):
        if not inDict:
            return default
        out = default
        parts = path.split(".")
        cur = inDict
        success = True
        for part in parts:
            # print(part, cur, part in cur, type(cur)==dict)
            if cur and type(cur) == list:
                index = 0
                try:
                    part = int(part)
                except:
                    pass
            if cur and ((type(cur) == dict and part in cur) or (type(cur) == list and 0 <= part < len(cur))):
                cur = cur[part]
            else:
                success = False
                break
        if success:
            out = cur
        if dataType:
            if dataType == 'int':
                out2 = default
                try:
                    out2 = int(out)
                except:
                    pass
                out = out2
        return out

    @staticmethod
    def compare_arrays(arr1, arr2):
        result_dict = {}

        set1 = set(arr1)
        set2 = set(arr2)

        result_dict["both"] = list(set1.intersection(set2))
        result_dict["unique_1"] = list(set1.difference(set2))
        result_dict["unique_2"] = list(set2.difference(set1))

        return result_dict

    @staticmethod
    def pluck(dicts, key):
        values = []
        for dictionary in dicts:
            if key in dictionary:
                values.append(dictionary[key])
        return values

    @staticmethod
    def guid():
        current_time = int(round(time.time() * 1000))
        guid = uuid.uuid1(node=current_time)
        guid_int = int(guid.int)
        return guid_int

    @staticmethod
    def split_overlap_array(array, size=10, overlap=2):
        result = []
        lenArray = len(array)
        step = size - overlap
        if step <= 0:
            # If step is zero or negative, return the whole array as one window
            if lenArray > 0:
                result.append(array)
            return result

        num_splits = lenArray // step + 1

        for i in range(num_splits):
            start = i * step
            end = start + size
            # print("Start/end/elements", start, end, array[start:end])
            result.append(array[start:end])
            if end >= lenArray:
                break
        return result

    @staticmethod
    def is_empty_vector(vector):
        return all(v == 0.0 for v in vector)

    @staticmethod
    def sort_dict_list(dict_list, key, ascending=True):
        """
        Sorts a list of dictionary objects based on the value of a dictionary element.
        :param dict_list: list of dictionaries
        :param key: key to sort by
        :return: sorted list of dictionaries
        """
        return sorted(dict_list, key=lambda x: x[key], reverse=not ascending)

    @staticmethod
    def get_url(url, headers=None, verbose=False, timeout=None):
        out = {"success": False, "code": -1, "errors": []}
        if not requests:
            print("No requests library")

            return out

        response = requests.get(url, params=None, cookies=None, headers=headers, timeout=timeout)
        out["code"] = response.status_code
        if out["code"] == 200:
            out["body"] = response.text
            try:
                out["json"] = response.json()
            except:
                pass
        else:
            out['errors'].append({"id": 198390129, "msg": response.text})

        return out

    @staticmethod
    def post_url(url, postData=None, jsonData=None, headers=None, cert=None, key=None, returnContent=False, isPut=False, verbose=False, timeout=None):
        out = {"success": False, "body": None, "json": None, "code": -1, "errors": []}
        response = out
        if not requests:
            msg = "No requests library in Utils"
            print(msg)
            out['errors'].append({"id": 142674, "msg": msg})
            return out
        if not headers:
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en_US",
            }
        if verbose:
            print("url", url, "headers", headers, "jsonData", jsonData)
        try:
            if isPut:
                response = requests.put(url, headers=headers, json=jsonData, data=postData, cert=cert, timeout=timeout)
            else:
                response = requests.post(url, headers=headers, json=jsonData, data=postData, cert=cert, timeout=timeout)
            out["code"] = response.status_code
        except requests.exceptions.Timeout as e:
            msg = "TIMEOUT error"
            out['errors'].append({"id": 8329471, "msg": msg})
            out['code'] = 500

        if out["code"] == 200:
            out["success"] = True
            if not returnContent:
                out["body"] = response.text
                try:
                    out["json"] = response.json()
                except:
                    pass
            else:
                print("CONTENT", response.content)
                out["body"] = response.content
        else:
            out['errors'].append({"id": 19839009, "msg": f"HTTP FAIL: {url} Response:{response}"})

        return out

    @staticmethod
    def empty(val):
        out = True
        # print("TYPE", type(val))
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
            # print("LIST", val)
            if len(val) != 0:
                out = False
        elif valType == dict:
            # print("DICT", val)
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

    @staticmethod
    def _float(val, default=None):
        out = default
        try:
            out = float(val)
        except:
            pass
        return out

    @staticmethod
    def clean_tags(tags):
        out = []
        for tag in tags:
            out.append(tag.strip().lower().replace('"', ''))
        return out

    @staticmethod
    def datetime_str(date_obj=None, formatStr="%Y-%m-%d %H:%M:%S"):
        out = None
        import time

        if not date_obj:
            out = time.strftime(formatStr)
        else:
            out = time.strftime(formatStr, date_obj)
        return out

    @staticmethod
    def append_log(file_path, text_string):
        try:
            if not os.path.exists(file_path):
                open(file_path, 'w').close()
            with open(file_path, 'a') as f:
                f.write(Utils.datetime_str() + " | " + text_string + "\n")
        except Exception as e:
            print(f"ERROR append_log :{e}")

    @staticmethod
    def generate_convo_xml(convo: Conversation):
        xml = "<conversation id='%d'>" % (83945)
        # print("CONVO OPENAI", convo)
        participants = {}

        for line in convo.lines:
            if len(line) != 2:
                continue

            participant = "p%d" % (line[0])
            xml += "<%s>%s</%s>" % (participant, line[1], participant)

            if not participant in participants:
                participants[participant] = 0

            # Count number entries for each participant -- may need it later
            participants[participant] += 1

        xml += "</conversation>"
        return (xml, participants)

    @staticmethod
    def get_safe_tag(inStr, seperator=' '):
        # Remove non-alpha numeric
        pass1 = re.sub(r'\s{2,}|[^a-zA-Z0-9\s]', seperator, inStr)
        return re.sub(r'[^\w\s]|(?<=\s)\s*', '', pass1).lower().strip()

    @staticmethod
    def get_clean_tag_set(tags):
        try:
            cleanTags = set()

            for tag in tags:
                safeTag = Utils.get_safe_tag(tag)

                if len(safeTag) < 3 or len(safeTag) > 64:
                    continue

                cleanTags.add(safeTag)

            return list(cleanTags)
        except Exception as e:
            return []

    @staticmethod
    def safe_value(val):
        # If it's a numpy array, return as is, it's ok
        if isinstance(val, np.ndarray):
            return val

        if val is None:
            return 0.0

        if isinstance(val, (float, np.floating)):
            # Treat NaN/Inf as 0.0
            if not np.isfinite(val):
                return 0.0
        return val
