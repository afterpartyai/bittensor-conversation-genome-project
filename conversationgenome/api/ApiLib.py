verbose = False

import json
import random
import requests

from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

class ApiLib:
    verbose = False

    async def reserveConversation(self, hotkey):
        # Call Convo server and reserve a conversation
        if c.get('env', 'SYSTEM_MODE') == 'test':
            path = 'facebook-chat-data.json'
            f = open(path)
            body = f.read()
            f.close()
            convos = json.loads(body)
            convoKeys = list(convos.keys())
            convoTotal = len(convoKeys)
            selectedConvoKey = random.choice(convoKeys)
            selectedConvo = convos[selectedConvoKey]

            convo = {
                "guid":Utils.get(selectedConvo, "guid"),
                "participants": Utils.get(selectedConvo, "participants", ["p1","p2"]),
                "lines":Utils.get(selectedConvo, "lines"),
            }
        else:
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en_US",
            }
            jsonData = { }
            postData = None
            cert = None
            selectedConvo = {}
            read_host_url = c.get('env', 'CGP_API_READ_HOST', 'http://api.conversations.xyz')
            read_host_port = c.get('env', 'CGP_API_READ_PORT', '443')
            http_timeout = Utils._float(c.get('env', 'HTTP_TIMEOUT', 60))
            url = f"{read_host_url}:{read_host_port}/api/v1/conversation/reserve"
            response = None
            try:
                response = requests.post(url, headers=headers, json=jsonData, data=postData, cert=cert, timeout=http_timeout)
            except requests.exceptions.Timeout as e:
                bt.logging.error(f"reserveConversation timeout error: {e}")
            maxLines = Utils._int(c.get('env', 'MAX_CONVO_LINES', 300))
            if response and response.status_code == 200:
                selectedConvo = response.json()
                #print("selectedConvo", selectedConvo)
            else:
                bt.logging.error(f"reserveConversation error. Response: {response}")
                return None


            convo = {
                "guid":Utils.get(selectedConvo, "guid"),
                "participants": Utils.get(selectedConvo, "participants", ["p1","p2"]),
                "lines":Utils.get(selectedConvo, "lines", [])[0:maxLines],
            }
        return convo

    async def completeConversation(self, hotkey, guid, dryrun=False):
        return True

    async def put_conversation_data(self, c_guid, jsonData):
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
