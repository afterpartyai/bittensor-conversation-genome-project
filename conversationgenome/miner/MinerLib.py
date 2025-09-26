verbose = False

from conversationgenome.ConfigLib import c
from conversationgenome.mock.MockBt import MockBt
from conversationgenome.task.Task import Task

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
