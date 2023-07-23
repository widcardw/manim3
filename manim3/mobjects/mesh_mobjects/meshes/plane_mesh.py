import numpy as np

from .parametric_surface_mesh import ParametricSurfaceMesh


class PlaneMesh(ParametricSurfaceMesh):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(
            func=lambda x, y: np.array((x, y, 0.0)),
            normal_func=lambda x, y: np.array((0.0, 0.0, 1.0)),
            u_range=(-1.0, 1.0),
            v_range=(-1.0, 1.0),
            resolution=(1, 1)
        )
