__all__ = ["SkiaMobject"]


#from abc import abstractmethod
from functools import reduce

import moderngl
import numpy as np
import skia
from trimesh import Trimesh

from ..geometries.plane_geometry import PlaneGeometry
from ..mobjects.textured_mesh_mobject import TexturedMeshMobject
from ..utils.context_singleton import ContextSingleton
from ..utils.lazy import lazy_property, lazy_property_initializer, lazy_property_initializer_writable
from ..custom_typing import *


class SkiaMobject(TexturedMeshMobject):
    #def __init__(self):
    #    super().__init__()
    #    self._enable_depth_test_ = False
    #    self._cull_face_ = "front_and_back"

    @lazy_property
    @classmethod
    def _geometry_(cls, frame: skia.Rect) -> Trimesh:
        frame_matrix = reduce(np.ndarray.__matmul__, (
            cls.matrix_from_translation(np.array((frame.centerX(), -frame.centerY(), 0.0))),
            cls.matrix_from_scale(np.array((frame.width() / 2.0, -frame.height() / 2.0, 1.0)))  # order?
        ))
        return PlaneGeometry().apply_transform(frame_matrix)

    @lazy_property_initializer_writable
    @classmethod
    def _enable_only_(cls) -> int:
        return moderngl.BLEND

    @lazy_property_initializer
    @classmethod
    def _frame_(cls) -> skia.Rect:
        return NotImplemented

    #@lazy_property
    #@classmethod
    #def _geometry_matrix_(cls, frame: skia.Rect) -> Matrix44Type:
    #    return reduce(np.ndarray.__matmul__, (
    #        cls.matrix_from_scale(np.array((frame.width() / 2.0, -frame.height() / 2.0, 1.0))),
    #        cls.matrix_from_translation(np.array((frame.centerX(), -frame.centerY(), 0.0)))
    #    ))

    @classmethod
    def _calculate_frame(
        cls,
        original_width: Real,
        original_height: Real,
        specified_width: Real | None,
        specified_height: Real | None,
        specified_frame_scale: Real | None
    ) -> skia.Rect:
        if specified_width is None and specified_height is None:
            width = original_width
            height = original_height
            if specified_frame_scale is not None:
                width *= specified_frame_scale
                height *= specified_frame_scale
        elif specified_width is not None and specified_height is None:
            width = specified_width
            height = specified_width / original_width * original_height
        elif specified_width is None and specified_height is not None:
            width = specified_height / original_height * original_width
            height = specified_height
        elif specified_width is not None and specified_height is not None:
            width = specified_width
            height = specified_height
        else:
            raise  # never
        rx = width / 2.0
        ry = height / 2.0
        return skia.Rect(l=-rx, t=-ry, r=rx, b=ry)

    @classmethod
    def _make_surface(cls, px_width: int, px_height: int) -> skia.Surface:
        # According to the documentation at `https://kyamagu.github.io/skia-python/tutorial`,
        # the default value of parameter `colorType` should be `skia.kRGBA_8888_ColorType`,
        # but it strangely defaults to `skia.kBGRA_8888_ColorType` in practice.
        # Passing in the parameter explicitly fixes this issue for now.

        # TODO: try using GPU rendering?
        surface = skia.Surface.MakeRaster(imageInfo=skia.ImageInfo.Make(
            width=px_width,
            height=px_height,
            ct=skia.kRGBA_8888_ColorType,
            at=skia.kUnpremul_AlphaType
        ))
        assert surface is not None
        return surface

    @classmethod
    def _make_texture(cls, image: skia.Image) -> moderngl.Texture:
        return ContextSingleton().texture(
            size=(image.width(), image.height()),
            components=image.imageInfo().bytesPerPixel(),
            data=image.tobytes(),
        )
