
from typing import Any, Callable

from .command import CLUCommand


class SimpleHandlerCommand(CLUCommand):

    def __init__(self, name, handler: Callable[[], Any], response: str) -> None:
        super().__init__(name)

        self._handler = handler
        self._response = response

    def execute(self, args: list[str]) -> str:
        self._handler()

        return self._response
