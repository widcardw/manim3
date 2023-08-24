import numpy as np

from ....constants.constants import UP
from ....utils.space_utils import SpaceUtils
from .parametric_surface_mesh import ParametricSurfaceMesh


class PlaneMesh(ParametricSurfaceMesh):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(
            func=SpaceUtils.increase_dimension,
            normal_func=lambda samples: np.repeat((UP,), len(samples), axis=0),
            u_range=(-1.0, 1.0),
            v_range=(-1.0, 1.0),
            resolution=(1, 1)
        )
