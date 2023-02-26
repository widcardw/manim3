__all__ = ["SceneMobject"]


import moderngl
import numpy as np


from ..geometries.geometry import Geometry
from ..geometries.plane_geometry import PlaneGeometry
from ..mobjects.mesh_mobject import MeshMobject
from ..rendering.config import ConfigSingleton
from ..rendering.framebuffer_batches import ColorFramebufferBatch
from ..scenes.scene import Scene
from ..scenes.scene_config import SceneConfig
from ..utils.lazy import (
    LazyWrapper,
    lazy_object
)


class SceneMobject(MeshMobject):
    __slots__ = ("_scene",)

    def __init__(
        self,
        scene_cls: type[Scene]
    ):
        super().__init__()
        self._scene: Scene = scene_cls()
        self.stretch_to_fit_size(np.array((*ConfigSingleton().frame_size, 0.0)))

    @lazy_object
    @staticmethod
    def _geometry_() -> Geometry:
        return PlaneGeometry()

    #@lazy_slot
    #@staticmethod
    #def _scene() -> Scene:
    #    return NotImplemented

    #def _update_dt(self, dt: Real):
    #    super()._update_dt(dt)  # TODO
    #    self._scene._update_dt(dt)

    def _render(
        self,
        scene_config: SceneConfig,
        target_framebuffer: moderngl.Framebuffer
    ) -> None:
        with ColorFramebufferBatch() as batch:
            self._scene._render_with_passes(self._scene._scene_config_, batch.framebuffer)
            self._color_map_ = LazyWrapper(batch.color_texture)
            super()._render(scene_config, target_framebuffer)
