import requests

from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c

from conversationgenome.api.ApiLib import ApiLib


class ConvoLib:
    async def get_conversation(self, hotkey):
        api = ApiLib()
        convo = await api.reserveConversation(hotkey)
        return convo

    async def getConvoPromptTemplate(self):
        return "Parse this"

    async def put_conversation(self, hotkey, c_guid, data, type="validator", batch_num=None, window=None):
        output = {
            "type": type,
            "mode": c.get('env', 'SYSTEM_MODE'),
            "model": c.get('env', 'OPENAI_MODEL'),
            "marker_id": c.get('env', 'MARKER_ID'),
            "convo_window_index": window,
            "hotkey": hotkey,
            "llm_type" : c.get('env', 'LLM_TYPE'),
            "scoring_version" : c.get('system', 'scoring_version'),
            "batch_num" : batch_num,
            "cgp_version": "0.1.0",
            "data": data,
        }
        api = ApiLib()
        result = await api.put_conversation_data(c_guid, output)
        return result
