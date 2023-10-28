
from abc import ABC, abstractmethod


class CLUCommand(ABC):

    def __init__(self, name) -> None:
        self.name = name

    @abstractmethod
    def execute(self, args: list[str]) -> str:
        raise NotImplementedError()