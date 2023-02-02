__all__ = [
    "Cube",
    "Dodecahedron",
    "Icosahedron",
    "Octahedron",
    "Polyhedron",
    "Tetrahedron"
]


import numpy as np

from manim3.utils.space_ops import SpaceOps

from ..custom_typing import (
    Mat4T,
    Vec2sT,
    Vec3sT
)
from ..mobjects.shape_mobject import ShapeMobject
from ..utils.shape import (
    LineString2D,
    MultiLineString2D,
    Shape
)


class Polyhedron(ShapeMobject):
    def __init__(self, vertices: Vec3sT, faces: np.ndarray[tuple[int, int], np.dtype[np.int_]]):
        super().__init__()
        for face in faces:
            matrix, coords = self._convert_coplanar_vertices(vertices[face])
            # Append the last point to form a closed ring
            ring_coords = np.append(coords, coords[0, None], axis=0)
            shape = ShapeMobject(Shape(MultiLineString2D([LineString2D(ring_coords)])))
            shape.apply_transform(matrix)
            self.add(shape)
        self.set_style(apply_phong_lighting=True)

    @classmethod
    def _convert_coplanar_vertices(cls, vertices: Vec3sT) -> tuple[Mat4T, Vec2sT]:
        assert len(vertices) >= 3
        # We first choose three points that define the plane.
        # Instead of choosing `vertices[:3]`, we choose `vertices[:2]` and the geometric centroid,
        # in order to reduce the chance that they happen to be colinear.
        # The winding order should be counterclockwise.
        origin = vertices[0]
        x_axis = SpaceOps.normalize(vertices[1] - vertices[0])
        z_axis = SpaceOps.normalize(np.cross(x_axis, np.average(vertices, axis=0) - origin))
        y_axis = np.cross(z_axis, x_axis)
        rotation_matrix = np.vstack((x_axis, y_axis, z_axis)).T

        transformed = (np.linalg.inv(rotation_matrix) @ (vertices - origin).T).T
        assert np.isclose(transformed[:, 2], 0.0).all(), "Vertices are not coplanar"

        matrix = np.identity(4)
        matrix[:3, :3] = rotation_matrix
        matrix[:3, 3] = origin
        return matrix, transformed[:, :2]


# The five platonic solids are ported from manim community
# /manim/mobject/three_d/polyhedra.py
# All these polyhedrons have all points sitting on the unit sphere.
class Tetrahedron(Polyhedron):
    def __init__(self):
        super().__init__(
            vertices=(1.0 / np.sqrt(3.0)) * np.array((
                (1.0, 1.0, 1.0),
                (1.0, -1.0, -1.0),
                (-1.0, 1.0, -1.0),
                (-1.0, -1.0, 1.0)
            )),
            faces=np.array((
                (0, 1, 2),
                (3, 0, 2),
                (1, 0, 3),
                (2, 1, 3)
            ))
        )


class Cube(Polyhedron):
    def __init__(self):
        super().__init__(
            vertices=(1.0 / np.sqrt(3.0)) * np.array((
                (1.0, 1.0, 1.0),
                (1.0, 1.0, -1.0),
                (1.0, -1.0, 1.0),
                (1.0, -1.0, -1.0),
                (-1.0, 1.0, 1.0),
                (-1.0, 1.0, -1.0),
                (-1.0, -1.0, 1.0),
                (-1.0, -1.0, -1.0),
            )),
            faces=np.array((
                (0, 2, 3, 1),
                (4, 5, 7, 6),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 4, 6, 2),
                (1, 3, 7, 5)
            ))
        )


class Octahedron(Polyhedron):
    def __init__(self):
        super().__init__(
            vertices=np.array((
                (1.0, 0.0, 0.0),
                (-1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, -1.0, 0.0),
                (0.0, 0.0, 1.0),
                (0.0, 0.0, -1.0)
            )),
            faces=np.array((
                (0, 2, 4),
                (2, 1, 4),
                (1, 3, 4),
                (3, 0, 4),
                (0, 3, 5),
                (3, 1, 5),
                (1, 2, 5),
                (2, 0, 5)
            ))
        )


class Dodecahedron(Polyhedron):
    def __init__(self):
        unit_a = (1.0 + np.sqrt(5.0)) / 2.0
        unit_b = -(1.0 - np.sqrt(5.0)) / 2.0
        super().__init__(
            vertices=(1.0 / np.sqrt(3.0)) * np.array((
                (1.0, 1.0, 1.0),
                (1.0, 1.0, -1.0),
                (1.0, -1.0, 1.0),
                (1.0, -1.0, -1.0),
                (-1.0, 1.0, 1.0),
                (-1.0, 1.0, -1.0),
                (-1.0, -1.0, 1.0),
                (-1.0, -1.0, -1.0),
                (0.0, unit_a, unit_b),
                (0.0, unit_a, -unit_b),
                (0.0, -unit_a, unit_b),
                (0.0, -unit_a, -unit_b),
                (unit_b, 0.0, unit_a),
                (-unit_b, 0.0, unit_a),
                (unit_b, 0.0, -unit_a),
                (-unit_b, 0.0, -unit_a),
                (unit_a, unit_b, 0.0),
                (unit_a, -unit_b, 0.0),
                (-unit_a, unit_b, 0.0),
                (-unit_a, -unit_b, 0.0)
            )),
            faces=np.array((
                (8, 0, 16, 1, 9),
                (9, 5, 18, 4, 8),
                (10, 6, 19, 7, 11),
                (11, 3, 17, 2, 10),
                (12, 0, 8, 4, 13),
                (13, 6, 10, 2, 12),
                (14, 3, 11, 7, 15),
                (15, 5, 9, 1, 14),
                (16, 0, 12, 2, 17),
                (17, 3, 14, 1, 16),
                (18, 5, 15, 7, 19),
                (19, 6, 13, 4, 18)
            ))
        )


class Icosahedron(Polyhedron):
    def __init__(self):
        unit_a = np.sqrt(50.0 + 10.0 * np.sqrt(5.0)) / 10.0
        unit_b = np.sqrt(50.0 - 10.0 * np.sqrt(5.0)) / 10.0
        super().__init__(
            vertices=np.array((
                (0.0, unit_a, unit_b),
                (0.0, unit_a, -unit_b),
                (0.0, -unit_a, unit_b),
                (0.0, -unit_a, -unit_b),
                (unit_b, 0.0, unit_a),
                (-unit_b, 0.0, unit_a),
                (unit_b, 0.0, -unit_a),
                (-unit_b, 0.0, -unit_a),
                (unit_a, unit_b, 0.0),
                (unit_a, -unit_b, 0.0),
                (-unit_a, unit_b, 0.0),
                (-unit_a, -unit_b, 0.0)
            )),
            faces=np.array((
                (0, 8, 1),
                (1, 10, 0),
                (2, 11, 3),
                (3, 9, 2),
                (4, 0, 5),
                (5, 2, 4),
                (6, 3, 7),
                (7, 1, 6),
                (8, 4, 9),
                (9, 6, 8),
                (10, 7, 11),
                (11, 5, 10),
                (8, 0, 4),
                (0, 10, 5),
                (11, 2, 5),
                (2, 9, 4),
                (9, 3, 6),
                (3, 11, 7),
                (10, 1, 7),
                (1, 8, 6)
            ))
        )
