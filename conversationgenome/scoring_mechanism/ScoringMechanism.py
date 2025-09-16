from abc import ABC, abstractmethod

from pydantic import BaseModel


class ScoringMechanism(BaseModel, ABC):
    @abstractmethod
    async def evaluate(self, conversation):
        pass
