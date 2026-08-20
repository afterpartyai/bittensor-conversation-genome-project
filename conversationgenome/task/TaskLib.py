from typing import Any
from typing import Optional

from conversationgenome import __version__ as CGP_VERSION
from conversationgenome.api.ApiLib import ApiLib
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_factory import LOCKED_LLM_TYPE
from conversationgenome.llm.llm_openai import DEFAULT_MODEL


class TaskLib:
    async def put_task(self, *, hotkey: str, task_bundle_id: str, task_id: str, neuron_type: str, batch_number: int, data: Any, api_key: Optional[str] = None) -> None:
        locked = c.get("system", "llm_overrides_locked", False)

        llm_type = LOCKED_LLM_TYPE if locked else c.get('llm', 'type')
        llm_type_override = c.get("env", "LLM_TYPE_OVERRIDE")

        if llm_type_override and not locked:
            llm_type = llm_type_override

        llm_model = DEFAULT_MODEL if locked else c.get('env', llm_type.upper() + "_MODEL")
        embeddings_model = c.get('llm', 'embeddings_model', "text-embedding-3-large")
        embeddings_model_override = c.get("env", "OPENAI_EMBEDDINGS_MODEL_OVERRIDE")

        if embeddings_model_override and not locked:
            embeddings_model = embeddings_model_override

        output = {
            "mode": c.get('env', 'SYSTEM_MODE'),
            "model": llm_model,
            "embeddings_model": embeddings_model,
            "marker_id": c.get('env', 'MARKER_ID'),
            "llm_type": llm_type,
            "scoring_version": c.get('system', 'scoring_version'),
            "cgp_version": CGP_VERSION,
            "netuid": c.get("system", "netuid"),
            "hotkey": hotkey,
            "neuron_type": neuron_type,
            "task_id": task_id,
            "batch_number": batch_number,
        }

        output['data'] = data
        api = ApiLib()
        result = await api.put_task_data(task_bundle_id, output, api_key=api_key)

        return result
