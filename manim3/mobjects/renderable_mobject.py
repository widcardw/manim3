from abc import abstractmethod

from ..cameras.camera import Camera
from ..cameras.perspective_camera import PerspectiveCamera
from ..lazy.lazy import Lazy
from ..mobjects.mobject import (
    Mobject,
    MobjectMeta
)
from ..rendering.framebuffer import (
    OpaqueFramebuffer,
    TransparentFramebuffer
)
from ..rendering.gl_buffer import UniformBlockBuffer


class RenderableMobject(Mobject):
    __slots__ = ()

    @MobjectMeta.register(
        interpolate_method=NotImplemented
    )
    @Lazy.variable_shared
    @classmethod
    def _is_transparent_(cls) -> bool:
        return False

    @Lazy.variable
    @classmethod
    def _camera_uniform_block_buffer_(cls) -> UniformBlockBuffer:
        # Keep updated with `Scene._camera._camera_uniform_block_buffer_`.
        return NotImplemented

    @abstractmethod
    def _render(
        self,
        target_framebuffer: OpaqueFramebuffer | TransparentFramebuffer
    ) -> None:
        pass

    @property
    def is_transparent(self) -> bool:
        return self._is_transparent_.value