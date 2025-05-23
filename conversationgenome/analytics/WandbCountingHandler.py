import logging


class WandbCountingHandler(logging.Handler):
    def __init__(self, wandb_lib_instance):
        super().__init__()
        self.wandb_lib = wandb_lib_instance

    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.wandb_lib.log({"bt_log": log_entry})
        except Exception as e:
            print(f"Logging handler error: {e}")
