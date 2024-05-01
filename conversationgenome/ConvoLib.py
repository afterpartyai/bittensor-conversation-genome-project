import requests

from conversationgenome.Utils import Utils
from conversationgenome.ConfigLib import c

from conversationgenome.ApiLib import ApiLib


class ConvoLib:
    async def get_conversation(self, hotkey):
        api = ApiLib()
        convo = await api.reserveConversation(hotkey)
        return convo

    async def getConvoPromptTemplate(self):
        return "Parse this"

    async def put_conversation(self, hotkey, c_guid, data, type="validator", batch_num=None):
        output = {
            "type": type,
            "mode": c.get('env', 'SYSTEM_MODE'),
            "model": c.get('env', 'OPENAI_MODEL'),
            "hotkey": hotkey,
            "llm_type" : c.get('env', 'LLM_TYPE'),
            "batch_num" : batch_num,
            "data": data,
        }
        api = ApiLib()
        result = await api.put_conversation_data(c_guid, output)
        return result
