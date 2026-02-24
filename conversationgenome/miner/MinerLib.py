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
    bt.logging.set_debug(True)
elif c.get('env', 'FORCE_LOG') == 'info':
    bt.logging.set_default(True)


class MinerLib:
    verbose = False

    async def do_mining(self, task: Task):
        print(f"Miner: Received {task.type} task for mining...")
        bt.logging.info(f"Miner: Received {task.type} task for mining...")

        result = await task.mine()

        bt.logging.info(f"Miner: Successfully mined {task.type} task. Returning results to validator...")

        return result
