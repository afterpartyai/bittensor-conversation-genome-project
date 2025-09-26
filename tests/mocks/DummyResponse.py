from tests.mocks.DummyAxon import DummyAxon


class DummyResponse:
    def __init__(self, hotkey, uuid, status_code, output=None):
        self.axon = DummyAxon(hotkey, uuid)
        self.dendrite = type("Dendrite", (), {"status_code": status_code})()
        self.cgp_output = output