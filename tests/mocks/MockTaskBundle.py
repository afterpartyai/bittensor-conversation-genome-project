# tests/mocks/MockTaskBundle.py
from unittest.mock import AsyncMock, MagicMock


class MockTask:
    def __init__(self, guid="mock-task-guid", bundle_guid="mock-bundle-guid", type="mock-type"):
        self.guid = guid
        self.bundle_guid = bundle_guid
        self.type = type
        self.input = MagicMock()
        self.input.data = MagicMock()
        self.input.data.window_idx = 0
        self.input.data.lines = [(0, "mock line")]
        self.input.data.participants = ["mock_participant"]
        self.input.data.prompt = "mock prompt"
        self.input.data.min_convo_windows = 1
        self.input.data.indexed_windows = [(0, [(0, "mock line")])]
        self.prompt_chain = []
        self.example_output = {}

    async def mine(self):
        return {"tags": ["mock_tag"], "vectors": {"mock_tag": [0.1]}}


class MockTaskBundle:
    def __init__(self, guid="mock-bundle-guid", num_tasks=3):
        self.guid = guid
        self.type = "mock-type"
        self.input = MagicMock()
        self.input.data = MagicMock()
        self.input.data.indexed_windows = [(i, [(i, f"mock line {i}")]) for i in range(num_tasks)]
        self.input.data.lines = [(i, f"mock line {i}") for i in range(num_tasks)]
        self.input.data.participants = ["mock_participant"]
        self.input.data.prompt = "mock prompt"
        self.input.data.min_convo_windows = 1
        self.input.metadata = MagicMock()
        self.prompt_chain = []
        self.example_output = {}

    def is_ready(self):
        return True

    async def setup(self):
        pass

    def to_mining_tasks(self, number_of_tasks_per_bundle):
        return [MockTask(guid=f"mock-task-{i}", bundle_guid=self.guid) for i in range(number_of_tasks_per_bundle)]

    async def format_results(self, miner_result):
        return miner_result

    def generate_result_logs(self, miner_result):
        return "mock result logs"

    async def evaluate(self, miner_responses):
        scores = [{"hotkey": f"hk{i}", "adjustedScore": 1.0, "final_miner_score": 1.0} for i in range(len(miner_responses))]
        ranks = [1 for _ in range(len(miner_responses))]
        return scores, ranks
