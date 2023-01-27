__all__ = [
    "LineString2D",
    "LineString3D",
    "MultiLineString2D",
    "MultiLineString3D",
    "Shape"
]


from abc import abstractmethod
from functools import reduce
from typing import (
    Generator,
    Generic,
    TypeVar
)

import numpy as np
import shapely.geometry
import shapely.ops

from ..custom_typing import (
    FloatsT,
    Real,
    Vec2T,
    Vec3T,
    Vec2sT,
    Vec3sT
)
from ..utils.lazy import (
    LazyBase,
    lazy_property,
    lazy_property_writable
)


_VecT = TypeVar("_VecT", bound=Vec2T | Vec3T)
_VecsT = TypeVar("_VecsT", bound=Vec2sT | Vec3sT)


class ShapeInterpolant(Generic[_VecT, _VecsT], LazyBase):
    @lazy_property
    @staticmethod
    def _lengths_() -> FloatsT:
        return NotImplemented

    @lazy_property
    @staticmethod
    def _length_(lengths: FloatsT) -> float:
        return max(lengths.sum(), 1e-6)

    @lazy_property
    @staticmethod
    def _length_knots_(lengths: FloatsT, length: float) -> FloatsT:
        return lengths.cumsum() / length

    @abstractmethod
    def interpolate_point(self, alpha: Real) -> _VecT:
        pass

    @abstractmethod
    def interpolate_shape(self, other: "ShapeInterpolant", alpha: Real) -> "ShapeInterpolant":
        pass

    @abstractmethod
    def partial(self, start: Real, end: Real) -> "ShapeInterpolant":
        pass

    @classmethod
    def _integer_interpolate(cls, array: FloatsT, target: Real) -> tuple[int, float]:
        """
        Assumed that `array` is already sorted, and that `0 <= array[0] <= target <= array[-1]`
        Returns `(i, (target - array[i - 1]) / (array[i] - array[i - 1]))` such that
        `0 <= i <= len(array) - 1` and `array[i - 1] <= target <= array[i]`,
        where we've interpreted `array[-1]` as 0.
        """
        if not len(array):
            return 0, 0.0
        index = int(np.searchsorted(array, target))
        if index == 0:
            try:
                return 0, target / array[0]
            except ZeroDivisionError:
                return 0, 0.0
        if index == len(array):
            return len(array) - 1, 1.0
        try:
            return index, (target - array[index - 1]) / (array[index] - array[index - 1])
        except ZeroDivisionError:
            return index, 0.0


class LineString(ShapeInterpolant[_VecT, _VecsT]):
    def __init__(self, coords: _VecsT):
        super().__init__()
        # We first normalize the input,
        # which is to remove redundant adjacent points to ensure
        # all segments have non-zero lengths.
        #if not len(coords):
        #    kind = "empty"
        #    simplified_coords = coords
        #else:
        #    points: list[Vec2T] = [coords[0]]
        #    current_point = coords[0]
        #    for point in coords:
        #        if np.isclose(np.linalg.norm(point - current_point), 0.0):
        #            continue
        #        current_point = point
        #        points.append(point)
        #    if len(points) == 1:
        #        kind = "point"
        #    elif not np.isclose(np.linalg.norm(points[-1] - points[0]), 0.0):
        #        kind = "line_string"
        #    else:
        #        #points.pop()
        #        assert len(points) >= 3
        #        kind = "linear_ring"
        #    simplified_coords = np.array(points)

        assert len(coords)
        self._coords_ = coords
        #self._kind_ = kind

    @lazy_property_writable
    @staticmethod
    def _coords_() -> _VecsT:
        return NotImplemented

    @lazy_property
    @staticmethod
    def _kind_(coords: _VecsT) -> str:
        if len(coords) == 1:
            return "point"
        if not np.isclose(np.linalg.norm(coords[-1] - coords[0]), 0.0):
            return "line_string"
        return "linear_ring"

    @lazy_property
    @staticmethod
    def _shapely_component_(kind: str, coords: _VecsT) -> shapely.geometry.base.BaseGeometry:
        if kind == "point":
            return shapely.geometry.Point(coords[0])
        if len(coords) == 2:
            return shapely.geometry.LineString(coords)
        return shapely.geometry.Polygon(coords)

    @lazy_property
    @staticmethod
    def _lengths_(coords: _VecsT) -> FloatsT:
        return np.linalg.norm(coords[1:] - coords[:-1], axis=1)

    @classmethod
    def _lerp(cls, vec_0: _VecT, vec_1: _VecT, alpha: Real) -> _VecT:
        return (1.0 - alpha) * vec_0 + alpha * vec_1

    def interpolate_point(self, alpha: Real) -> _VecT:
        index, residue = self._integer_interpolate(self._length_knots_, alpha)
        return self._lerp(self._coords_[index], self._coords_[index + 1], residue)

    def interpolate_shape(self, other: "LineString", alpha: Real) -> "LineString":
        all_knots = sorted({0.0, *self._length_knots_, *other._length_knots_})
        return LineString(np.array([
            self._lerp(self.interpolate_point(knot), other.interpolate_point(knot), alpha)
            for knot in all_knots
        ]))

    def partial(self, start: Real, end: Real) -> "LineString":
        coords = self._coords_
        knots = self._length_knots_
        start_index, start_residue = self._integer_interpolate(knots, start)
        end_index, end_residue = self._integer_interpolate(knots, end)
        if start_index == end_index and start_residue == end_residue:
            new_coords = [
                self._lerp(coords[start_index], coords[start_index + 1], start_residue)
            ]
        else:
            new_coords = [
                self._lerp(coords[start_index], coords[start_index + 1], start_residue),
                *coords[start_index + 1:end_index + 1],
                self._lerp(coords[end_index], coords[end_index + 1], end_residue)
            ]
        return LineString(np.array(new_coords))


class MultiLineString(ShapeInterpolant[_VecT, _VecsT]):
    def __init__(self, children: list[LineString[_VecT, _VecsT]] | None = None):
        super().__init__()
        if children is not None:
            self._children_.extend(children)

    @lazy_property
    @staticmethod
    def _children_() -> list[LineString[_VecT, _VecsT]]:
        return []

    @lazy_property
    @staticmethod
    def _lengths_(children: list[LineString[_VecT, _VecsT]]) -> FloatsT:
        return np.array([child._length_ for child in children])

    def interpolate_point(self, alpha: Real) -> _VecT:
        index, residue = self._integer_interpolate(self._length_knots_, alpha)
        return self._children_[index].interpolate_point(residue)

    def interpolate_shape(self, other: "MultiLineString[_VecT, _VecsT]", alpha: Real):
        children = self._children_
        knots_0 = self._length_knots_
        knots_1 = other._length_knots_
        current_knot = 0.0
        start_0 = 0.0
        start_1 = 0.0
        ptr_0 = 0
        ptr_1 = 0
        new_children: list[LineString[_VecT, _VecsT]] = []
        while ptr_0 < len(knots_0) and ptr_1 < len(knots_1):
            knot_0 = knots_0[ptr_0]
            knot_1 = knots_1[ptr_1]
            next_knot = min(knot_0, knot_1)
            end_0 = (next_knot - current_knot) / (knot_0 - current_knot)
            end_1 = (next_knot - current_knot) / (knot_1 - current_knot)
            child_0 = children[ptr_0].partial(start_0, end_0)
            child_1 = children[ptr_1].partial(start_1, end_1)
            new_children.append(child_0.interpolate_shape(child_1, alpha))

            if knot_0 == next_knot:
                start_0 = 0.0
                ptr_0 += 1
            else:
                start_0 = end_0
            if knot_1 == next_knot:
                start_1 = 0.0
                ptr_1 += 1
            else:
                start_1 = end_1
            current_knot = next_knot

        return self.__class__(new_children)

    def partial(self, start: Real, end: Real):
        children = self._children_
        if not children:
            return self.__class__()

        knots = self._length_knots_
        start_index, start_residue = self._integer_interpolate(knots, start)
        end_index, end_residue = self._integer_interpolate(knots, end)
        if start_index == end_index:
            new_children = [children[start_index].partial(start_residue, end_residue)]
        else:
            new_children = [
                children[start_index].partial(start_residue, 1.0),
                *children[start_index + 1:end_index],
                children[end_index].partial(0.0, end_residue)
            ]
        return self.__class__(new_children)


#class LineString2D(LineString[])


#class MultiLineString(ShapeInterpolant[LineString, _VecT, _VecsT]):
#    pass


#class Polygon(ShapeInterpolant[LineString]):
#    def __init__(self, line_strings: list[LineString] | None = None):
#        if line_strings is None:
#            line_strings = []
#        simplified_line_strings = [
#            line_string for line_string in line_strings
#            if line_string._kind_ != "empty"
#        ]
#        if not len(simplified_line_strings):
#            kind = "empty"
#        else:
#            shell = simplified_line_strings[0]
#            if shell._kind_ in ("")
#
#            points: list[Vec2T] = [coords[0]]
#            current_point = coords[0]
#            for point in coords:
#                if np.isclose(np.linalg.norm(point - current_point), 0.0):
#                    continue
#                current_point = point
#                points.append(point)
#            if len(points) == 1:
#                kind = "point"
#            elif not np.isclose(np.linalg.norm(points[-1] - points[0]), 0.0):
#                kind = "line_string"
#            else:
#                #points.pop()
#                assert len(points) >= 3
#                kind = "linear_ring"
#            simplified_coords = np.array(points)
#
#        super().__init__(simplified_line_strings)
#        self._kind_ = kind
#
#    @lazy_property_writable
#    @staticmethod
#    def _kind_() -> str:
#        return NotImplemented
#
#    @lazy_property
#    @staticmethod
#    def _shapely_obj_(children: list[LineString]) -> shapely.geometry.Polygon:
#        return shapely.geometry.Polygon(
#            children[0]._coords_,
#            [line_string._coords_ for line_string in children[1:]]
#        )
#
#    #@lazy_property
#    #@staticmethod
#    #def _shapely_boundary_(children: list[LineString]) -> list[shapely.geometry.LineString]:
#    #    return [
#    #        shapely.geometry.LineString(line_string._coords_)
#    #        for line_string in children
#    #    ]
#
#    #@lazy_property
#    #@staticmethod
#    #def _triangulation_(children: list[LineString]) -> tuple[VertexIndexType, Vec2sT]:
#    #    ring_coords_list = [np.array(ring._coords_, dtype=np.float32) for ring in children]
#    #    coords = np.concatenate(ring_coords_list)
#    #    if not len(coords):
#    #        return np.zeros((0,), dtype=np.uint32), np.zeros((0, 2))
#
#    #    ring_ends = np.cumsum([len(ring_coords) for ring_coords in ring_coords_list], dtype=np.uint32)
#    #    return triangulate_float32(coords, ring_ends), coords
#
#
#class Polygons(ShapeInterpolant[Polygon]):
#    @lazy_property
#    @staticmethod
#    def _shapely_obj_(children: list[Polygon]) -> shapely.geometry.GeometryCollection:
#        return shapely.geometry.GeometryCollection([
#            polygon._shapely_obj_
#            for polygon in children
#        ])
#
#    #@lazy_property
#    #@staticmethod
#    #def _shapely_boundary_(children: list[Polygon]) -> list[shapely.geometry.LineString]:
#    #    return [
#    #        shapely_line_string
#    #        for polygon in children
#    #        for shapely_line_string in polygon._shapely_boundary_
#    #    ]
#
#    #@lazy_property
#    #@staticmethod
#    #def _triangulation_(children: list[Polygon]) -> tuple[VertexIndexType, Vec2sT]:
#    #    if not children:
#    #        return np.zeros((0,), dtype=np.uint32), np.zeros((0, 2))
#
#    #    item_list: list[tuple[VertexIndexType, Vec2sT]] = []
#    #    coords_len = 0
#    #    for child in children:
#    #        indices, coords = child._triangulation_
#    #        item_list.append((indices + coords_len, coords))
#    #        coords_len += len(coords)
#    #    indices_list, coords_list = zip(*item_list)
#    #    return np.concatenate(indices_list), np.concatenate(coords_list)


class LineString2D(LineString[Vec2T, Vec2sT]):
    pass


class LineString3D(LineString[Vec3T, Vec3sT]):
    pass


class MultiLineString2D(MultiLineString[Vec2T, Vec2sT]):
    pass


class MultiLineString3D(MultiLineString[Vec3T, Vec3sT]):
    pass


class Shape(LazyBase):
    def __init__(self, multi_line_string: MultiLineString2D | None = None):
        super().__init__()
        if multi_line_string is not None:
            self._multi_line_string_ = multi_line_string

    def __and__(self, other: "Shape"):
        return self.intersection(other)

    def __or__(self, other: "Shape"):
        return self.union(other)

    def __sub__(self, other: "Shape"):
        return self.difference(other)

    def __xor__(self, other: "Shape"):
        return self.symmetric_difference(other)

    @lazy_property_writable
    @staticmethod
    def _multi_line_string_() -> MultiLineString2D:
        return MultiLineString2D()

    @lazy_property
    @staticmethod
    def _multi_line_string_3d_(multi_line_string: MultiLineString2D) -> MultiLineString3D:
        return MultiLineString3D([
            LineString3D(np.insert(line_string._coords_, 2, 0.0, axis=1))
            for line_string in multi_line_string._children_
        ])

    @classmethod
    def _from_shapely_obj(cls, shapely_obj: shapely.geometry.base.BaseGeometry) -> "Shape":
        return Shape(MultiLineString2D(list(cls._get_line_strings_from_shapely_obj(shapely_obj))))

    @classmethod
    def _get_line_strings_from_shapely_obj(cls, shapely_obj: shapely.geometry.base.BaseGeometry) -> Generator[LineString2D, None, None]:
        if isinstance(shapely_obj, shapely.geometry.Point | shapely.geometry.LineString):
            yield LineString2D(np.array(shapely_obj.coords))
        elif isinstance(shapely_obj, shapely.geometry.Polygon):
            shapely_obj = shapely.geometry.polygon.orient(shapely_obj)  # TODO: needed?
            yield LineString2D(np.array(shapely_obj.exterior.coords))
            for interior in shapely_obj.interiors:
                yield LineString2D(np.array(interior.coords))
        elif isinstance(shapely_obj, shapely.geometry.base.BaseMultipartGeometry):
            for child in shapely_obj.geoms:
                yield from cls._get_line_strings_from_shapely_obj(child)
        else:
            raise TypeError

    @lazy_property
    @staticmethod
    def _shapely_obj_(multi_line_string: MultiLineString2D) -> shapely.geometry.base.BaseGeometry:
        return Shape._to_shapely_object(multi_line_string)

    #@lazy_property
    #@staticmethod
    #def _shapely_boundary_(polygons: Polygons) -> list[shapely.geometry.LineString]:
    #    return polygons._shapely_boundary_

    @classmethod
    def _to_shapely_object(cls, multi_line_string: MultiLineString2D) -> shapely.geometry.base.BaseGeometry:
        return reduce(shapely.geometry.base.BaseGeometry.__xor__, [
            line_string._shapely_component_
            for line_string in multi_line_string._children_
        ], shapely.geometry.GeometryCollection())

    def interpolate_point(self, alpha: Real) -> Vec2T:
        return self._multi_line_string_.interpolate_point(alpha)

    def interpolate_shape(self, other: "Shape", alpha: Real) -> "Shape":
        return Shape(self._multi_line_string_.interpolate_shape(other._multi_line_string_, alpha))

    def partial(self, start: Real, end: Real) -> "Shape":
        return Shape(self._multi_line_string_.partial(start, end))

    #@lazy_property
    #@staticmethod
    #def _triangulation_(polygons: Polygons) -> tuple[VertexIndexType, Vec2sT]:
    #    return polygons._triangulation_

    # operations ported from shapely

    @property
    def area(self) -> float:
        return self._shapely_obj_.area

    def distance(self, other: "Shape") -> float:
        return self._shapely_obj_.distance(other._shapely_obj_)

    def hausdorff_distance(self, other: "Shape") -> float:
        return self._shapely_obj_.hausdorff_distance(other._shapely_obj_)

    @property
    def length(self) -> float:
        return self._shapely_obj_.length

    @property
    def centroid(self) -> Vec2T:
        return np.array(self._shapely_obj_.centroid)

    @property
    def convex_hull(self) -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.convex_hull)

    @property
    def envelope(self) -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.envelope)

    def buffer(
        self,
        distance: Real,
        quad_segs: int = 16,
        cap_style: str = "round",
        join_style: str = "round",
        mitre_limit: Real = 5.0,
        single_sided: bool = False
    ) -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.buffer(
            distance=distance,
            quad_segs=quad_segs,
            cap_style=cap_style,
            join_style=join_style,
            mitre_limit=mitre_limit,
            single_sided=single_sided
        ))

    def intersection(self, other: "Shape") -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.intersection(other._shapely_obj_))

    def union(self, other: "Shape") -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.union(other._shapely_obj_))

    def difference(self, other: "Shape") -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.difference(other._shapely_obj_))

    def symmetric_difference(self, other: "Shape") -> "Shape":
        return Shape._from_shapely_obj(self._shapely_obj_.symmetric_difference(other._shapely_obj_))