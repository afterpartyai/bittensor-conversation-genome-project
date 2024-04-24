import random
import json

from conversationgenome.Utils import Utils
from conversationgenome.ConfigLib import c

bt = None
try:
    import bittensor as bt
except:
    if verbose:
        print("bittensor not installed")
    bt = MockBt()

import wandb

class WandbLib:
    verbose = False

    def init_wandb(self, data=None):
        if c.get("env", "WANDB_DISABLE"):
            return
        api = wandb.Api()
        wandb_api_key = c.get("env", "WANDB_API_KEY")
        if not wandb_api_key:
            raise ValueError("Please log in to wandb using `wandb login` or set the WANDB_API_KEY environment variable.")
        run = 5
        bt.logging.info("INIT WANDB", wandb_api_key)

        my_uid = 2
        PROJECT_NAME = 'cgp_test_run'
        __version__ = "3.3.0"
        run_name = f'cgp/validator-{my_uid}-{__version__}'
        hotkey = "abc-123"
        uid = 7
        uuid = "456-789"
        config = {
            "uid": uid,
            "uuid": uuid,
            "hotkey": hotkey,
            "run_name": 10,
            "version": __version__,
            "type": 'validator',
        }
        old_config={
              "learning_rate": 0.02,
              "architecture": "CNN",
              "dataset": "CIFAR-100",
              #"epochs": epochs,
        }
        epochs = 10
        wandb.init(
              project=PROJECT_NAME,
              name=run_name, #f"conversationgenome/cguid_{c_guid}",
              config=config
        )
    def log_example_data(self, data):
        print("Do log....")
        epochs = 10
        offset = random.random() / 5
        for epoch in range(2, epochs):
            acc = 1 - 2 ** -epoch - random.random() / epoch - offset
            loss = 2 ** -epoch + random.random() / epoch + offset

            wandb.log({"acc": acc, "loss": loss})
        wandb.log({"miner_uuid":10, "miner_hotkey":"a8348-123123", "score": random.random()})

    def log(self, data):
        if self.verbose:
            print("WANDB LOG", data)
        wandb.log(data)

    def end_log_wandb(self):
        # Mark the run as finished
        wandb.finish()

