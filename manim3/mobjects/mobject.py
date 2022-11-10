from abc import ABC
from dataclasses import dataclass
from functools import reduce
import pyrr
from typing import Generator, Iterable, Iterator, TypeVar

import numpy as np
from scipy.spatial.transform import Rotation

from ..cameras.camera import Camera
from ..shader_utils import ShaderData
from ..constants import ORIGIN
from ..typing import *


__all__ = [
    "BoundingBox3D",
    "Mobject",
    "Group"
]


T = TypeVar("T")


@dataclass
class BoundingBox3D:
    origin: Vector3Type
    radius: Vector3Type


class Mobject(ABC):
    def __init__(self: Self) -> None:
        self.parents: list[Self] = []
        self.children: list[Self] = []

        self.matrix: pyrr.Matrix44 = self.init_matrix()

        # shader context settings
        self.enable_depth_test: bool = True
        self.enable_blend: bool = True
        self.cull_face: str = "back"
        self.wireframe: bool = False

    def init_matrix(self: Self) -> pyrr.Matrix44:
        return pyrr.Matrix44.identity()

    def __iter__(self: Self) -> Iterator[Self]:
        return iter(self.get_children())

    # family

    def get_parents(self: Self) -> list[Self]:
        return self.parents

    def get_children(self: Self) -> list[Self]:
        return self.children

    def _bind_child(self: Self, node: Self, index: int | None = None) -> Self:
        if node.includes(self):
            raise ValueError(f"'{node}' has already included '{self}'")
        if index is not None:
            self.children.insert(index, node)
        else:
            self.children.append(node)
        node.parents.append(self)
        return self

    def _unbind_child(self: Self, node: Self) -> Self:
        self.children.remove(node)
        node.parents.remove(self)
        return self

    @staticmethod
    def remove_redundancies(l: Iterable[T]) -> list[T]:
        """
        Used instead of list(set(l)) to maintain order
        Keeps the first occurrence of each element
        """
        return list(dict.fromkeys(l))

    def _iter_ancestors(self: Self) -> Generator[Self, None, None]:
        yield self
        for parent in self.get_parents():
            yield from parent._iter_ancestors()

    def _iter_descendents(self: Self) -> Generator[Self, None, None]:
        yield self
        for child in self.get_children():
            yield from child._iter_descendents()

    def get_ancestors(self: Self, *, broadcast: bool = True) -> list[Self]:  # TODO: order
        if not broadcast:
            return [self]
        return self.remove_redundancies(self._iter_ancestors())

    def get_descendents(self: Self, *, broadcast: bool = True) -> list[Self]:
        if not broadcast:
            return [self]
        return self.remove_redundancies(self._iter_descendents())

    def includes(self: Self, node: Self) -> bool:
        return node in self._iter_descendents()

    #def clear_bindings(self) -> None:
    #    for parent in self.parent:
    #        parent.children.remove(self)
    #    for child in self.children:
    #        child.parent.remove(self)
    #    #for parent in self.parent:
    #    #    for child in self.children:
    #    #        parent._bind_child(child, loop_check=False)
    #    self.parent.clear()
    #    self.children.clear()

    def index(self: Self, node: Self) -> int:
        return self.get_children().index(node)

    def insert(self: Self, index: int, *nodes: Self) -> Self:
        for i, node in enumerate(nodes, start=index):
            self._bind_child(node, index=i)
        return self

    def add(self: Self, *nodes: Self) -> Self:
        for node in nodes:
            self._bind_child(node)
        return self

    def remove(self: Self, *nodes: Self) -> Self:
        for node in nodes:
            self._unbind_child(node)
        return self

    def pop(self: Self, index: int = -1) -> Self:
        node = self.children[index]
        self._unbind_child(node)
        return node

    def clear(self: Self) -> Self:
        for child in self.children:
            self._unbind_child(child)
        return self

    def clear_parents(self: Self) -> Self:
        for parent in self.parent:
            parent._unbind_child(self)
        return self

    # matrix & transform

    @staticmethod
    def matrix_from_translation(vector: Vector3Type) -> pyrr.Matrix44:
        return pyrr.Matrix44.from_translation(vector)

    @staticmethod
    def matrix_from_scale(factor_vector: Vector3Type) -> pyrr.Matrix44:
        return pyrr.Matrix44.from_scale(factor_vector)

    @staticmethod
    def matrix_from_rotation(rotation: Rotation) -> pyrr.Matrix44:
        return pyrr.Matrix44.from_matrix33(rotation.as_matrix())

    def get_local_sample_points(self: Self) -> Vector3ArrayType:
        # Implemented in subclasses
        return np.zeros((0, 3))

    def get_aabb(self: Self, **kwargs) -> BoundingBox3D:
        points = [
            pyrr.matrix44.apply_to_vector(
                mobject.matrix, point
            )
            for mobject in self.get_descendents(**kwargs)
            for point in mobject.get_local_sample_points()
        ]
        minimum, maximum = pyrr.aabb.create_from_points(points)
        return BoundingBox3D(
            origin=(maximum + minimum) / 2.0,
            radius=(maximum - minimum) / 2.0
        )

    def get_boundary_point(self: Self, direction: Vector3Type, **kwargs) -> Vector3Type:
        aabb = self.get_aabb(**kwargs)
        return aabb.origin + direction * aabb.radius

    def apply_matrix(
        self: Self,
        matrix: pyrr.Matrix44,
        *,
        about_point: Vector3Type | None = None,
        about_edge: Vector3Type | None = None,
        **kwargs
    ) -> Self:
        if about_point is None:
            if about_edge is None:
                about_edge = ORIGIN
            about_point = self.get_boundary_point(about_edge)
        elif about_edge is not None:
            raise AttributeError("Cannot specify both parameters `about_point` and `about_edge`")

        #if np.isclose(np.linalg.det(matrix), 0.0):
        #    warnings.warn("Applying a singular matrix transform")
        matrix = reduce(pyrr.Matrix44.__matmul__, (
            self.matrix_from_translation(-about_point),
            matrix,
            self.matrix_from_translation(about_point)
        ))
        for mobject in self.get_descendents(**kwargs):
            mobject.matrix = mobject.matrix @ matrix
        return self

    def shift(self: Self, vector: Vector3Type, **kwargs) -> Self:
        matrix = self.matrix_from_translation(vector)
        self.apply_matrix(matrix, **kwargs)
        return self

    def scale(self: Self, factor: Real | Vector3Type, **kwargs) -> Self:
        if isinstance(factor, Real):
            factor_vector = pyrr.Vector3()
            factor_vector.fill(factor)
        else:
            factor_vector = pyrr.Vector3(factor)
        matrix = self.matrix_from_scale(factor_vector)
        self.apply_matrix(matrix, **kwargs)
        return self

    def rotate(self: Self, rotation: Rotation, **kwargs) -> Self:
        matrix = self.matrix_from_rotation(rotation)
        self.apply_matrix(matrix, **kwargs)
        return self

    # shader

    def setup_shader_data(self: Self, camera: Camera) -> ShaderData | None:
        # To be implemented in subclasses
        return None


class Group(Mobject):
    def __init__(self: Self, *mobjects: Mobject):
        super().__init__()
        self.add(*mobjects)
