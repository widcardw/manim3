from ..animation.rates.rate import Rate
from ..animation.animation import Animation
from .parallel import Parallel


class Series(Parallel):
    __slots__ = ()

    def __init__(
        self,
        *animations: Animation,
        rate: Rate | None = None,
        lag_time: float = 0.0,
        lag_ratio: float = 1.0
    ) -> None:
        super().__init__(
            *animations,
            rate=rate,
            lag_time=lag_time,
            lag_ratio=lag_ratio
        )