import logging
import time

from conversationgenome import __version__ as init_version
from conversationgenome.analytics.WandbCountingHandler import WandbCountingHandler

verbose = False

from conversationgenome.ConfigLib import c
from conversationgenome.mock.MockBt import MockBt
from conversationgenome.utils.Utils import Utils

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
    PROJECT_NAME = 'conversationgenome'
    ENTITY = 'afterparty'
    MAX_LOG_LINES = 95000

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WandbLib, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.verbose = False
        self.log_line_count = 0
        self.run_config = None
        self.run_name_prefix = None
        self.__version__ = "3.3.0"
        self.run = None
        self.bt_logger_attached = False

        self._initialized = True

    def init_wandb(self, config=None, data=None):
        wandb_enabled = Utils._int(c.get('env', 'WAND_ENABLED'), 1)
        if not wandb_enabled:
            bt.logging.debug("Weights and Biases Logging Disabled -- Skipping Initialization")
            return

        my_hotkey = 12345
        my_uid = -1
        netuid = -1

        if config:
            # initialize data:
            try:
                wallet = bt.wallet(config=config)
                subtensor = bt.subtensor(config=config)
                netuid = config.netuid
                metagraph = subtensor.metagraph(config.netuid)
                my_hotkey = wallet.hotkey.ss58_address
                my_uid = metagraph.hotkeys.index(my_hotkey)
            except Exception as e:
                print(f"ERROR 8618322 -- WandB init error: {e}")

        wandb_api_key = c.get("env", "WANDB_API_KEY")
        if not wandb_api_key:
            raise ValueError("Please log in to wandb using `wandb login` or set the WANDB_API_KEY environment variable.")

        bt.logging.info("INIT WANDB", wandb_api_key)

        try:
            self.__version__ = init_version
        except:
            print(f"ERROR 1277289 -- WandB version init error: {e}")

        self.run_name_prefix = f'cgp/validator-{my_uid}-{self.__version__}'
        self.run_config = {
            "uid": my_uid,
            "hotkey": my_hotkey,
            "version": self.__version__,
            "type": 'validator',
            "netuid": netuid,
        }

        self.start_new_run()
        self.attach_bt_logger()

    def start_new_run(self):
        current_timestamp_ms = int(time.time() * 1000)

        self.run = wandb.init(
            project=self.PROJECT_NAME,
            name=f"{self.run_name_prefix}-{current_timestamp_ms}",  # f"conversationgenome/cguid_{c_guid}",
            entity=self.ENTITY,
            config=self.run_config,
            reinit=True,
        )

    # this was needed because WandB was logging Bittensor logs in the run, but did not use this class.
    # It made it impossible to know when to create a new run.
    # This handler makes sure Bittensor logs are sent to WandB using this class.
    def attach_bt_logger(self):
        if self.bt_logger_attached:
            return  # To make sure we don't attach it twice

        handler = WandbCountingHandler(self)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        bt_logger = logging.getLogger("bittensor")
        bt_logger.addHandler(handler)
        bt_logger.setLevel(logging.INFO)

        self.bt_logger_attached = True

    def log(self, data):
        wandb_enabled = Utils._int(c.get('env', 'WAND_ENABLED'), 1)
        if wandb_enabled:
            if self.verbose:
                print("WANDB LOG", data)

            self.run.log(data)

            self.log_line_count += 1

            if self.log_line_count >= self.MAX_LOG_LINES:
                self.run.finish()
                self.log_line_count = 0
                self.start_new_run()
        else:
            bt.logging.debug("Weights and Biases Logging Disabled -- Skipping Log")
            return

    def end_log_wandb(self):
        # Mark the run as finished
        self.run.finish()
