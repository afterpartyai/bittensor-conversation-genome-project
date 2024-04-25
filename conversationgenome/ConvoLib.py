import requests

from conversationgenome.ApiLib import ApiLib


class ConvoLib:
    async def get_conversation(self, hotkey):
        api = ApiLib()
        convo = await api.reserveConversation(hotkey)
        return convo

    async def getConvoPromptTemplate(self):
        return "Parse this"

    async def markConversionComplete(self, hotkey, cguid, dryrun=False):
        api = ApiLib()
        result = await api.completeConversation(hotkey, cguid, dryrun=dryrun)
        return result

    async def put_conversation(self, hotkey, c_guid, data):
        output = {
            "hotkey": hotkey,
            "data": data,
        }
        api = ApiLib()
        result = await api.put_conversation_data(c_guid, output)
        return result
