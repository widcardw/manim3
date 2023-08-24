from ...mobjects.mobject.abouts.about import About
from ...mobjects.mobject.remodel_handlers.remodel_handler import RemodelHandler
from ...mobjects.mobject.mobject import (
    Mobject,
    RemodelBoundHandler
)
from ..animation.animation import Animation


class RemodelBase(Animation):
    __slots__ = ("_remodel_bound_handler",)

    def __init__(
        self,
        mobject: Mobject,
        remodel_handler: RemodelHandler,
        about: About | None = None,
        run_alpha: float = float("inf")
    ) -> None:
        super().__init__(
            run_alpha=run_alpha
        )
        self._remodel_bound_handler: RemodelBoundHandler = mobject._get_remodel_bound_handler(
            remodel_handler=remodel_handler,
            about=about
        )

    def updater(
        self,
        alpha: float
    ) -> None:
        self._remodel_bound_handler.remodel(alpha)
