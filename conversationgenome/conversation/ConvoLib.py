from conversationgenome import __version__ as CGP_VERSION
from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.api.models.conversation import Conversation
from conversationgenome.ConfigLib import c


class ConvoLib:
    verbose = False

    async def get_conversation(self, hotkey, api_key=None) -> Conversation:
        api = ApiLib()
        convo: Conversation = await api.reserveConversation(hotkey, api_key=api_key)
        return convo

    async def put_conversation(self, hotkey, c_guid, data, type="validator", batch_num=None, window=None, verbose=False):
        llm_type = c.get("llm", "type", "openai")
        llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")

        if llm_type_override:
            llm_type = llm_type_override

        llm_model = c.get('env', llm_type.upper() + "_MODEL")
        embeddings_model = "text-embedding-3-large"
        embeddings_model = c.get("llm", "embeddings_model", "text-embedding-3-large")
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
            "llm_type": llm_type,
            "scoring_version": c.get('system', 'scoring_version'),
            "batch_num": batch_num,
            "cgp_version": CGP_VERSION,
            "netuid": c.get("system", "netuid"),
        }

        output['data'] = data
        api = ApiLib()
        result = await api.put_conversation_data(c_guid, output)

        return result
