verbose = False

import copy
from typing import Optional

from conversationgenome.api.models.conversation import Conversation
from conversationgenome.ConfigLib import c
from conversationgenome.llm.llm_factory import get_llm_backend
from conversationgenome.miner.default_prompts import get_task_default_prompt
from conversationgenome.mock.MockBt import MockBt
from conversationgenome.task.Task import Task
from conversationgenome.utils.Utils import Utils

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

if c.get('env', 'FORCE_LOG') == 'debug':
    bt.logging.enable_debug(True)
elif c.get('env', 'FORCE_LOG') == 'info':
    bt.logging.enable_default(True)


class MinerLib:
    verbose = False

    async def do_mining(self, task: Task):
        bt.logging.info(f"Miner: Received {task.type} task for mining...")

        result = await task.mine()

        bt.logging.info(f"Miner: Successfully mined {task.type} task. Returning results to validator...")

        return result

    async def do_old_mining(self, conversation_guid, window_idx, conversation_window, minerUid, task_prompt: Optional[str], task_type: Optional[str], dryrun=False):
        out = {"uid": minerUid, "tags": [], "profiles": [], "convoChecksum": 11}

        llml = get_llm_backend()
        lines = copy.deepcopy(conversation_window)

        # Default prompts is fetched here so no miners are penalized by an non-updated validator.
        # When the migrations to tasks is fully complete, the default prompt will come from the tasks implementation and this will be removed.
        if not task_prompt:
            task_prompt = get_task_default_prompt(task_type=task_type)

            # If no prompt is returned, it means the task type is not supported and we fallback to the default prompt later
            if task_prompt is None:
                task_type = None

        try:
            conversation = Conversation(guid=conversation_guid, lines=conversation_window, miner_task_prompt=task_prompt, miner_task_type=task_type)
        except Exception:
            bt.logging.error(f"Wrong task type {task_type} provided to miner. Falling back to None.")
            conversation = Conversation(guid=conversation_guid, lines=lines, miner_task_prompt=task_prompt, miner_task_type=None)

        result = await llml.conversation_to_metadata(conversation=conversation)

        out["tags"] = result.tags
        out["vectors"] = result.vectors

        num_tags = len(Utils.get(out, 'tags', []))
        bt.logging.info(f"Miner: Mined {num_tags} tags")

        if self.verbose:
            bt.logging.debug(f"MINED TAGS: {out['tags']}")

        return out
