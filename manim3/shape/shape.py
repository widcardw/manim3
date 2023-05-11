from functools import reduce
from typing import (
    Callable,
    Iterable,
    Iterator
)

from mapbox_earcut import triangulate_float32
import numpy as np
import shapely.geometry
import shapely.validation

from ..custom_typing import (
    Vec2T,
    Vec2sT,
    VertexIndexT
)
from ..lazy.lazy import (
    Lazy,
    LazyObject
)
from ..shape.line_string import (
    LineString,
    MultiLineString
)
from ..utils.space import SpaceUtils


class Shape(LazyObject):
    __slots__ = ()

    def __init__(
        self,
        args_iterable: Iterable[tuple[Vec2sT, bool]] | None = None
    ) -> None:
        super().__init__()
        if args_iterable is not None:
            self._multi_line_string_ = MultiLineString(
                LineString(SpaceUtils.increase_dimension(points), is_ring=is_ring)
                for points, is_ring in args_iterable
                if len(points)
            )

    def __and__(
        self,
        other: "Shape"
    ) -> "Shape":
        return self.intersection(other)

    def __or__(
        self,
        other: "Shape"
    ) -> "Shape":
        return self.union(other)

    def __sub__(
        self,
        other: "Shape"
    ) -> "Shape":
        return self.difference(other)

    def __xor__(
        self,
        other: "Shape"
    ) -> "Shape":
        return self.symmetric_difference(other)

    @Lazy.variable
    @classmethod
    def _multi_line_string_(cls) -> MultiLineString:
        return MultiLineString()

    @Lazy.property_external
    @classmethod
    def _shapely_obj_(
        cls,
        _multi_line_string__line_strings_: list[LineString]
    ) -> shapely.geometry.base.BaseGeometry:

        def get_shapely_component(
            line_string: LineString
        ) -> shapely.geometry.base.BaseGeometry:
            points: Vec2sT = line_string._points_.value[:, :2]
            if len(points) == 1:
                return shapely.geometry.Point(points[0])
            if len(points) == 2:
                return shapely.geometry.LineString(points)
            return shapely.validation.make_valid(shapely.geometry.Polygon(points))

        return reduce(shapely.geometry.base.BaseGeometry.__xor__, (
            get_shapely_component(line_string)
            for line_string in _multi_line_string__line_strings_
        ), shapely.geometry.GeometryCollection())

    @Lazy.property_external
    @classmethod
    def _triangulation_(
        cls,
        shapely_obj: shapely.geometry.base.BaseGeometry
    ) -> tuple[VertexIndexT, Vec2sT]:

        def get_shapely_polygons(
            shapely_obj: shapely.geometry.base.BaseGeometry
        ) -> Iterator[shapely.geometry.Polygon]:
            if isinstance(shapely_obj, shapely.geometry.Point | shapely.geometry.LineString):
                pass
            elif isinstance(shapely_obj, shapely.geometry.Polygon):
                yield shapely_obj
            elif isinstance(shapely_obj, shapely.geometry.base.BaseMultipartGeometry):
                for child in shapely_obj.geoms:
                    yield from get_shapely_polygons(child)
            else:
                raise TypeError

        def get_polygon_triangulation(
            polygon: shapely.geometry.Polygon
        ) -> tuple[VertexIndexT, Vec2sT]:
            ring_points_list = [
                np.array(boundary.coords, dtype=np.float32)
                for boundary in [polygon.exterior, *polygon.interiors]
            ]
            points = np.concatenate(ring_points_list)
            if not len(points):
                return np.zeros((0,), dtype=np.uint32), np.zeros((0, 2))

            ring_ends = np.cumsum([len(ring_points) for ring_points in ring_points_list], dtype=np.uint32)
            return triangulate_float32(points, ring_ends), points

        def concatenate_triangulations(
            triangulations: list[tuple[VertexIndexT, Vec2sT]]
        ) -> tuple[VertexIndexT, Vec2sT]:
            if not triangulations:
                return np.zeros((0,), dtype=np.uint32), np.zeros((0, 2))

            offsets = np.cumsum((0, *(len(points) for _, points in triangulations[:-1])))
            all_index = np.concatenate([
                index + offset
                for (index, _), offset in zip(triangulations, offsets, strict=True)
            ], dtype=np.uint32)
            all_points = np.concatenate([
                points
                for _, points in triangulations
            ])
            return all_index, all_points

        return concatenate_triangulations([
            get_polygon_triangulation(polygon)
            for polygon in get_shapely_polygons(shapely_obj)
        ])

    @classmethod
    def from_multi_line_string(
        cls,
        multi_line_string: MultiLineString
    ) -> "Shape":
        result = Shape()
        result._multi_line_string_ = multi_line_string
        return result

    @classmethod
    def from_shapely_obj(
        cls,
        shapely_obj: shapely.geometry.base.BaseGeometry
    ) -> "Shape":

        def iter_args_from_shapely_obj(
            shapely_obj: shapely.geometry.base.BaseGeometry
        ) -> Iterator[tuple[Vec2sT, bool]]:
            if isinstance(shapely_obj, shapely.geometry.Point | shapely.geometry.LineString):
                yield np.array(shapely_obj.coords), False
            elif isinstance(shapely_obj, shapely.geometry.Polygon):
                shapely_obj = shapely.geometry.polygon.orient(shapely_obj)  # TODO: needed?
                yield np.array(shapely_obj.exterior.coords[:-1]), True
                for interior in shapely_obj.interiors:
                    yield np.array(interior.coords[:-1]), True
            elif isinstance(shapely_obj, shapely.geometry.base.BaseMultipartGeometry):
                for shapely_obj_component in shapely_obj.geoms:
                    yield from iter_args_from_shapely_obj(shapely_obj_component)
            else:
                raise TypeError

        return Shape(iter_args_from_shapely_obj(shapely_obj))

    def interpolate_point(
        self,
        alpha: float
    ) -> Vec2T:
        return self._multi_line_string_.interpolate_point(alpha)[:2]

    def partial(
        self,
        start: float,
        stop: float
    ) -> "Shape":
        return Shape.from_multi_line_string(self._multi_line_string_.partial(start, stop))

    @classmethod
    def get_interpolant(
        cls,
        shape_0: "Shape",
        shape_1: "Shape",
        *,
        has_inlay: bool = True
    ) -> "Callable[[float], Shape]":
        multi_line_string_interpolant = MultiLineString.get_interpolant(
            shape_0._multi_line_string_,
            shape_1._multi_line_string_,
            has_inlay=has_inlay
        )

        def interpolant(
            alpha: float
        ) -> Shape:
            return Shape.from_multi_line_string(multi_line_string_interpolant(alpha))

        return interpolant

    @classmethod
    def concatenate(
        cls,
        shapes: "Iterable[Shape]"
    ) -> "Shape":
        return Shape.from_multi_line_string(MultiLineString.concatenate(
            shape._multi_line_string_
            for shape in shapes
        ))

    # operations ported from shapely

    @property
    def shapely_obj(self) -> shapely.geometry.base.BaseGeometry:
        return self._shapely_obj_.value

    @property
    def area(self) -> float:
        return self.shapely_obj.area

    def distance(
        self,
        other: "Shape"
    ) -> float:
        return self.shapely_obj.distance(other.shapely_obj)

    def hausdorff_distance(
        self,
        other: "Shape"
    ) -> float:
        return self.shapely_obj.hausdorff_distance(other.shapely_obj)

    @property
    def length(self) -> float:
        return self.shapely_obj.length

    @property
    def centroid(self) -> Vec2T:
        return np.array(self.shapely_obj.centroid)

    @property
    def convex_hull(self) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.convex_hull)

    @property
    def envelope(self) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.envelope)

    def buffer(
        self,
        distance: float,
        quad_segs: int = 16,
        cap_style: str = "round",
        join_style: str = "round",
        mitre_limit: float = 5.0,
        single_sided: bool = False
    ) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.buffer(
            distance=distance,
            quad_segs=quad_segs,
            cap_style=cap_style,
            join_style=join_style,
            mitre_limit=mitre_limit,
            single_sided=single_sided
        ))

    def intersection(
        self,
        other: "Shape"
    ) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.intersection(other.shapely_obj))

    def union(
        self,
        other: "Shape"
    ) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.union(other.shapely_obj))

    def difference(
        self,
        other: "Shape"
    ) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.difference(other.shapely_obj))

    def symmetric_difference(
        self,
        other: "Shape"
    ) -> "Shape":
        return Shape.from_shapely_obj(self.shapely_obj.symmetric_difference(other.shapely_obj))
