from neurons.validator import Validator


class TestValidator(Validator):
    def __init__(self, config, *, block_override=None, skip_sync=True):
        self._skip_sync_flag = skip_sync
        self._block_override = block_override

        # Temporarily disable sync during init
        original_sync = self.sync
        if self._skip_sync_flag:
            self.sync = lambda: None

        super().__init__(config)

        if self._skip_sync_flag:
            self.sync = original_sync

    @property
    def block(self):
        if hasattr(self, "_block_override") and self._block_override is not None:
            return self._block_override
        return super().block