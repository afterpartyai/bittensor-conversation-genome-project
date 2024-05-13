import json
import random
import requests

from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c


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
            url = f"{read_host_url}:{read_host_port}/api/v1/conversation/reserve"
            response = requests.post(url, headers=headers, json=jsonData, data=postData, cert=cert)
            maxLines = Utils._int(c.get('env', 'MAX_CONVO_LINES', 300))
            if response.status_code == 200:
                selectedConvo = response.json()
                #print("selectedConvo", selectedConvo)
            else:
                print("ERROR", response)


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
        response = requests.put(url, headers=headers, json=jsonData)
        if response.status_code == 200:
            if self.verbose:
                print("PUT success", response.json())
        else:
            print("PUT ERROR", response)
        return True

if __name__ == "__main__":
    print("Test convo get")
    url = "https://www.google.com"
    body = Utils.get_url(url)
    print(body)
