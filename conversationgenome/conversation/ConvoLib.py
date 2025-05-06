import requests

from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.ConfigLib import c
from conversationgenome.utils.Utils import Utils


class ConvoLib:
    verbose = False

    async def get_conversation(self, hotkey, api_key=None):
        api = ApiLib()
        convo = await api.reserveConversation(hotkey, api_key=api_key)
        return convo

    async def put_conversation(self, hotkey, c_guid, data, type="validator", batch_num=None, window=None, verbose=False):
        llm_type = "openai"

        model = "gpt-4o"
        llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")
        if llm_type_override:
            llm_type = llm_type_override
            model = c.get("env", "OPENAI_MODEL")
        llm_model = c.get('env', llm_type.upper() + "_MODEL")

        embeddings_model = "text-embedding-3-large"
        embeddings_model_override = c.get("env", "OPENAI_EMBEDDINGS_MODEL_OVERRIDE")
        if embeddings_model_override:
            embeddings_model = embeddings_model_override

        output = {
            "type": type,
            "mode": c.get('env', 'SYSTEM_MODE'),
            "model": llm_model,
            "embeddings_model": embeddings_model,
            "marker_id": c.get('env', 'MARKER_ID'),
            "convo_window_index": window,
            "hotkey": hotkey,
            "llm_type": c.get('env', 'LLM_TYPE'),
            "scoring_version": c.get('system', 'scoring_version'),
            "batch_num": batch_num,
            "cgp_version": "0.2.0",
            "netuid": c.get("system", "netuid"),
        }
        if self.verbose or verbose:
            print("PUT CONFIG", output)
        output['data'] = data
        api = ApiLib()
        result = await api.put_conversation_data(c_guid, output)
        return result
