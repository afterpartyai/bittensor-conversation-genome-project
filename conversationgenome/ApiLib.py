import json
import random
import requests

from conversationgenome.Utils import Utils
from conversationgenome.ConfigLib import c


class ApiLib:
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
            #print("convoTotal", convoTotal)
            selectedConvoKey = random.choice(convoKeys)
            selectedConvo = convos[selectedConvoKey]
            #print("selectedConvo", selectedConvo)


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
            read_host_url = c.get('env', 'CGP_API_READ_HOST', 'http://api.conversationgenome.org')
            read_host_port = c.get('env', 'CGP_API_READ_PORT', '80')
            url = f"{read_host_url}:{read_host_port}/api/v1/conversation/reserve"
            response = requests.post(url, headers=headers, json=jsonData, data=postData, cert=cert)
            if response.status_code == 200:
                selectedConvo = response.json()
                #print("selectedConvo", selectedConvo)
            else:
                print("ERROR")


            convo = {
                "guid":Utils.get(selectedConvo, "guid"),
                "participants": Utils.get(selectedConvo, "participants", ["p1","p2"]),
                "lines":Utils.get(selectedConvo, "lines"),
            }
        return convo

    async def completeConversation(self, hotkey, guid, dryrun=False):
        return True


if __name__ == "__main__":
    print("Test convo get")
    url = "https://www.google.com"
    body = Utils.get_url(url)
    print(body)
