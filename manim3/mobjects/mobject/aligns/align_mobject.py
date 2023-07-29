from ....constants.constants import ORIGIN
from ....constants.custom_typing import NP_3f8
from ..mobject import Mobject
from .align_position import AlignPosition


class AlignMobject(AlignPosition):
    __slots__ = ()

    def __init__(
        self,
        mobject: Mobject,
        direction: NP_3f8 = ORIGIN,
        buff: float | NP_3f8 = 0.0
    ) -> None:
        super().__init__(
            position=mobject.get_bounding_box_position(direction),
            direction=direction,
            buff=buff
        )