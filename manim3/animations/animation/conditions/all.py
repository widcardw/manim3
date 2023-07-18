from typing import Iterable

from .condition import Condition


class All(Condition):
    __slots__ = ("_consitions",)

    def __init__(
        self,
        conditions: Iterable[Condition]
    ) -> None:
        super().__init__()
        self._consitions: list[Condition] = list(conditions)

    def _judge(self) -> bool:
        return all(condition._judge() for condition in self._consitions)
