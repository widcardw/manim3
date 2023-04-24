import numpy as np

from ..cameras.camera import Camera
from ..custom_typing import Mat4T
from ..lazy.interface import Lazy
from ..rendering.config import ConfigSingleton


class PerspectiveCamera(Camera):
    __slots__ = ()

    def __init__(
        self,
        *,
        width: float | None = None,
        height: float | None = None,
        near: float | None = None,
        far: float | None = None,
        altitude: float | None = None
    ) -> None:
        super().__init__()
        if width is not None:
            self._width_ = width
        if height is not None:
            self._height_ = height
        if near is not None:
            self._near_ = near
        if far is not None:
            self._far_ = far
        if altitude is not None:
            self._altitude_ = altitude

    @Lazy.variable_external
    @classmethod
    def _width_(cls) -> float:
        return ConfigSingleton().size.frame_width

    @Lazy.variable_external
    @classmethod
    def _height_(cls) -> float:
        return ConfigSingleton().size.frame_height

    @Lazy.variable_external
    @classmethod
    def _near_(cls) -> float:
        return ConfigSingleton().camera.near

    @Lazy.variable_external
    @classmethod
    def _far_(cls) -> float:
        return ConfigSingleton().camera.far

    @Lazy.variable_external
    @classmethod
    def _altitude_(cls) -> float:
        return ConfigSingleton().camera.altitude

    @Lazy.property_external
    @classmethod
    def _projection_matrix_(
        cls,
        width: float,
        height: float,
        near: float,
        far: float,
        altitude: float
    ) -> Mat4T:
        sx = 2.0 * altitude / width
        sy = 2.0 * altitude / height
        sz = -(far + near) / (far - near)
        tz = -2.0 * far * near / (far - near)
        return np.array((
            ( sx, 0.0,  0.0, 0.0),
            (0.0,  sy,  0.0, 0.0),
            (0.0, 0.0,   sz,  tz),
            (0.0, 0.0, -1.0, 0.0)
        ))
