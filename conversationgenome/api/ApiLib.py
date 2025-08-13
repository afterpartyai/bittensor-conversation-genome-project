verbose = False

import json
import random

import requests

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.ConfigLib import c
from conversationgenome.api.models.task import Task
from conversationgenome.mock.MockBt import MockBt
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

    async def reserveConversation(self, hotkey, api_key=None) -> Conversation:
        # Call Convo server and reserve a conversation
        if c.get('env', 'SYSTEM_MODE') == 'test':
            path = 'facebook-chat-data.json'
            f = open(path)
            body = f.read()
            f.close()
            convos = json.loads(body)
            convoKeys = list(convos.keys())
            selectedConvoKey = random.choice(convoKeys)
            selectedConvo = convos[selectedConvoKey]

            convo: Conversation = Conversation(
                guid=Utils.get(selectedConvo, "guid"),
                participants=Utils.get(selectedConvo, "participants", ["p1", "p2"]),
                lines=Utils.get(selectedConvo, "lines"),
            )
        else:
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en_US",
                "Authorization": "Bearer %s" % (str(api_key)),
            }

            jsonData = {}
            postData = None
            cert = None
            selectedConvo = {}
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

            maxLines = Utils._int(c.get('env', 'MAX_CONVO_LINES', 300))

            if response and response.status_code == 200:
                task: Task = Task(**response.json())
                # print("selectedConvo", selectedConvo)
            else:
                bt.logging.error(f"reserveConversation error. Response: {response}")
                return None

            # Until API and code is updated everywhere
            try:
                miner_task_prompt = task.prompt_chain[0].prompt_template
            except (IndexError, AttributeError, TypeError):
                miner_task_prompt = None

            convo: Conversation = Conversation(
                guid=str(task.guid),
                participants=task.participants,
                lines=task.lines[0:maxLines],
                miner_task_prompt=miner_task_prompt
            )

            if 'min_convo_windows' in selectedConvo:
                convo.min_convo_windows = Utils._int(Utils.get(selectedConvo, "min_convo_windows"))

        return convo

    async def completeConversation(self, hotkey, guid, dryrun=False) -> bool:
        return True

    async def put_conversation_data(self, c_guid, jsonData) -> bool:
        write_host_url = c.get('env', 'CGP_API_WRITE_HOST', 'https://db.conversations.xyz')
        write_host_port = c.get('env', 'CGP_API_WRITE_PORT', '443')
        url = f"{write_host_url}:{write_host_port}/api/v1/conversation/record/{c_guid}"

        if self.verbose:
            print(f"PUTTING TO {url}")

        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }

        http_timeout = Utils._float(c.get('env', 'HTTP_TIMEOUT', 60))

        try:
            response = requests.put(url, headers=headers, json=jsonData, timeout=http_timeout)

            if response.status_code == 200:
                if self.verbose:
                    print("PUT success", response.json())
            else:
                bt.logging.error("ERROR: 7283917: put_conversation_data ERROR", response)
                return False
        except Exception as e:
            bt.logging.error("ERROR: 7283918: put_conversation_data RESPONSE", e)
            return False

        return True


if __name__ == "__main__":
    print("Test convo get")
    url = "https://www.google.com"
    body = Utils.get_url(url)
    print(body)
