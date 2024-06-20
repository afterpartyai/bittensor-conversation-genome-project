import random
import json

verbose = False


from conversationgenome.utils.Utils import Utils
from conversationgenome.ConfigLib import c
from conversationgenome.mock.MockBt import MockBt

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

wandb = None
try:
    import wandb
except:
    print("wandb not installed")


class WandbLib:
    verbose = False

    def init_wandb(self, config=None, data=None):
        my_hotkey=12345
        my_uid = -1
        try:
            wallet= bt.wallet()
            subtensor = bt.subtensor()
            metagraph = subtensor.metagraph()
        except Exception as e:
            print(f"ERROR 7592656 -- WandB init error: {e}")

        if config:
            #initialize data:
            try:
                wallet = bt.wallet(config=config)
                subtensor = bt.subtensor(config=config)
                metagraph = subtensor.metagraph(config.netuid)
                my_hotkey=wallet.hotkey.ss58_address
                my_uid = metagraph.hotkeys.index(my_hotkey)
            except Exception as e:
                print(f"ERROR 8618322 -- WandB init error: {e}")
                

        if c.get("env", "WANDB_DISABLE"):
            return
        api = wandb.Api()
        wandb_api_key = c.get("env", "WANDB_API_KEY")
        if not wandb_api_key:
            raise ValueError("Please log in to wandb using `wandb login` or set the WANDB_API_KEY environment variable.")

        bt.logging.info("INIT WANDB", wandb_api_key)

        PROJECT_NAME = 'conversationgenome'
        __version__ = "3.3.0"
        run_name = f'cgp/validator-{my_uid}-{__version__}'
        config = {
            "uid": my_uid,
            "hotkey": my_hotkey,
            "version": __version__,
            "type": 'validator',
        }
        wandb.init(
              project=PROJECT_NAME,
              name=run_name, #f"conversationgenome/cguid_{c_guid}",
              entity='afterparty',
              config=config
        )

    def log(self, data):
        if self.verbose:
            print("WANDB LOG", data)
        wandb.log(data)

    def end_log_wandb(self):
        # Mark the run as finished
        wandb.finish()

