verbose = False

import json

import requests

from conversationgenome.ConfigLib import c
from conversationgenome.mock.MockBt import MockBt
from conversationgenome.task_bundle.task_bundle_factory import try_parse_task_bundle
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.utils.Utils import Utils

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()


class ApiLib:
    verbose = False

    async def reserve_task_bundle(self, hotkey, api_key=None) -> TaskBundle:
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
            "Authorization": "Bearer %s" % (str(api_key)),
        }

        jsonData = {}
        postData = None
        cert = None
        read_host_url = c.get('env', 'CGP_API_READ_HOST', 'https://api.conversations.xyz')
        read_host_port = c.get('env', 'CGP_API_READ_PORT', '443')
        http_timeout = Utils._float(c.get('env', 'HTTP_TIMEOUT', 60))
        options_str = c.get('env', 'CGP_API_OPTIONS', '')
        url = f"{read_host_url}:{read_host_port}/api/v1/conversation/reserve"

        if len(options_str) > 0:
            options = options_str.split(",")
            bt.logging.info(f"Read API options: {options}")
            if "22" in options:
                url += "?options=22"

        response = None

        try:
            response = requests.post(url, headers=headers, json=jsonData, data=postData, cert=cert, timeout=http_timeout)
        except requests.exceptions.Timeout as e:
            bt.logging.error(f"reserveConversation timeout error: {e}")

        if response and response.status_code == 200:
            data = response.json()
            task_bundle: TaskBundle = try_parse_task_bundle(data)

            if not task_bundle:
                bt.logging.error("reserveConversation error. No task bundle")
                return None
        else:
            bt.logging.error(f"reserveConversation error. Response: {response}")
            return None

        return task_bundle

    async def put_task_data(self, id, json_data) -> bool:
        write_host_url = c.get('env', 'CGP_API_WRITE_HOST', 'https://db.conversations.xyz')
        write_host_port = c.get('env', 'CGP_API_WRITE_PORT', '443')
        url = f"{write_host_url}:{write_host_port}/api/v1/conversation/record/{id}"

        if self.verbose:
            print(f"PUTTING TO {url}")

        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }

        http_timeout = Utils._float(c.get('env', 'HTTP_TIMEOUT', 60))

        try:
            response = requests.put(url, headers=headers, json=json_data, timeout=http_timeout)

            if response.status_code == 200:
                if self.verbose:
                    print("PUT success", response.json())
            else:
                bt.logging.error("ERROR: 7283917: put_task_data ERROR", response)
                return False
        except Exception as e:
            bt.logging.error("ERROR: 7283918: put_task_data RESPONSE", e)
            return False

        return True
