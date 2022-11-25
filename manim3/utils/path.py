from abc import abstractmethod
from typing import Callable, Generic, TypeVar

import numpy as np
import scipy.integrate
import scipy.interpolate
import skia

from ..utils.lazy import LazyMeta, lazy_property, lazy_property_initializer
from ..custom_typing import *


__all__ = ["Path"]


_T = TypeVar("_T", bound="CurveInterpolantBase")


def interp1d(x: FloatArrayType, y: FloatArrayType, tol: Real = 1e-6, **kwargs) -> scipy.interpolate.interp1d:
    # Append one more sample point at each side in order to prevent from floating error.
    # Also solves the issue where we have only one sample, while the original function requires at least two.
    # Assumed that `x` is already sorted.
    new_x = np.array([x[0] - tol, *x, x[-1] + tol])
    new_y = np.array([y[0], *y, y[-1]])
    return scipy.interpolate.interp1d(new_x, new_y, **kwargs)


class CurveInterpolantBase(metaclass=LazyMeta):
    @lazy_property_initializer
    @abstractmethod
    def _a_final_() -> float:
        raise NotImplementedError

    @lazy_property_initializer
    @abstractmethod
    def _l_final_() -> float:
        raise NotImplementedError

    @abstractmethod
    def a_to_p(self, a: Real) -> Vector2Type:
        raise NotImplementedError

    @abstractmethod
    def a_to_l(self, a: Real) -> float:
        raise NotImplementedError

    @abstractmethod
    def l_to_a(self, l: Real) -> float:
        raise NotImplementedError

    def a_ratio_to_p(self, a_ratio: Real) -> Vector2Type:
        return self.a_to_p(a_ratio * self._a_final_)

    def a_ratio_to_l_ratio(self, a_ratio: Real) -> float:
        try:
            return self.a_to_l(a_ratio * self._a_final_) / self._l_final_
        except ZeroDivisionError:
            return 0.0

    def l_ratio_to_a_ratio(self, l_ratio: Real) -> float:
        try:
            return self.l_to_a(l_ratio * self._l_final_) / self._a_final_
        except ZeroDivisionError:
            return 0.0

    @abstractmethod
    def partial_by_a(self, a: Real):
        raise NotImplementedError

    def partial_by_l(self, l: Real):
        return self.partial_by_a(self.l_to_a(l))

    def partial_by_a_ratio(self, a_ratio: Real):
        return self.partial_by_a(a_ratio * self._a_final_)

    def partial_by_l_ratio(self, l_ratio: Real):
        return self.partial_by_l(l_ratio * self._l_final_)


class CurveInterpolant(CurveInterpolantBase, Generic[_T]):
    """
    A general tree-structured curve interpolant.

    Typically, a curve has an alpha parametrization (`a`, defined on [0, `a_final`])
    and a length parametrization (`l`, defoned on [0, `l_final`]).
    A bunch of translation methods are defined.
    """
    def __init__(self, children: list[_T] | None = None):
        if children is None:
            children = []
        self._children_.extend(children)
        #a_knots = np.zeros(1)
        #l_knots = np.zeros(1)
        #self._a_knots: FloatArrayType = a_knots
        #self._l_knots: FloatArrayType = l_knots
        #self._a_interpolator: Callable[[Real], tuple[int, float]] = self.integer_interpolator(a_knots)
        #self._l_interpolator: Callable[[Real], tuple[int, float]] = self.integer_interpolator(l_knots)
        #self._a_final: float = a_knots[-1]
        #self._l_final: float = l_knots[-1]
        #self.data_require_updating: bool = True
        #self.update_data()

    #def update_data(self):
    #    if self.data_require_updating:
    #        #children = self.get_updated_children()
    #        #self._children = children
    #        children = self._children
    #        a_knots = np.insert(np.cumsum([child.a_final for child in children]), 0, 0.0)
    #        l_knots = np.insert(np.cumsum([child.l_final for child in children]), 0, 0.0)
    #        self._a_knots = a_knots
    #        self._l_knots = l_knots
    #        self._a_interpolator = self.integer_interpolator(a_knots)
    #        self._l_interpolator = self.integer_interpolator(l_knots)
    #        self._a_final = a_knots[-1]
    #        self._l_final = l_knots[-1]
    #        self.data_require_updating = False
    #    return self

    #def get_updated_children(self) -> list[_T]:
    #    return self._children

    @lazy_property_initializer
    def _children_() -> list[_T]:
        return []
        #self.update_data()
        #return self._children

    @lazy_property
    def _a_knots_(cls, children: list[_T]) -> FloatArrayType:
        #self.update_data()
        return np.insert(np.cumsum([child._a_final_ for child in children]), 0, 0.0)

    @lazy_property
    def _l_knots_(cls, children: list[_T]) -> FloatArrayType:
        #self.update_data()
        return np.insert(np.cumsum([child._l_final_ for child in children]), 0, 0.0)

    @lazy_property
    def _a_final_(cls, a_knots: FloatArrayType) -> float:
        #self.update_data()
        return a_knots[-1]

    @lazy_property
    def _l_final_(cls, l_knots: FloatArrayType) -> float:
        #self.update_data()
        return l_knots[-1]

    @lazy_property
    def _a_interpolator_(cls, a_knots: FloatArrayType) -> Callable[[Real], tuple[int, float]]:
        return cls.integer_interpolator(a_knots)

    @lazy_property
    def _l_interpolator_(cls, l_knots: FloatArrayType) -> Callable[[Real], tuple[int, float]]:
        return cls.integer_interpolator(l_knots)

    def a_interpolate(self, a: Real) -> tuple[int, float]:
        #self.update_data()
        return self._a_interpolator_(a)

    def l_interpolate(self, l: Real) -> tuple[int, float]:
        #self.update_data()
        return self._l_interpolator_(l)

    def a_to_p(self, a: Real) -> Vector2Type:
        i, a_remainder = self.a_interpolate(a)
        assert a_remainder
        return self._children_[i].a_to_p(a_remainder)

    def a_to_l(self, a: Real) -> float:
        i, a_remainder = self.a_interpolate(a)
        l = self._l_knots_[i]
        if a_remainder:
            l += self._children_[i].a_to_l(a_remainder)
        return l

    def l_to_a(self, l: Real) -> float:
        i, l_remainder = self.l_interpolate(l)
        a = self._a_knots_[i]
        if l_remainder:
            a += self._children_[i].l_to_a(l_remainder)
        return a

    def partial_by_a(self, a: Real):
        i, a_remainder = self.a_interpolate(a)
        children = self._children_[:i]
        if a_remainder:
            children.append(self._children_[i].partial_by_a(a_remainder))
        return self.__class__(children=children)

    @classmethod
    def integer_interpolator(cls, array: FloatArrayType) -> Callable[[Real], tuple[int, float]]:
        def wrapped(target: Real) -> tuple[int, float]:
            """
            Assumed that `array` is already sorted, and that `array[0] <= target <= array[-1]`
            If `target == array[0]`, returns `(0, 0.0)`.
            Otherwise, returns `(i, target - array[i])` such that
            `0 <= i < len(array) - 1` and `array[i] < target <= array[i + 1]`.
            """
            index = int(interp1d(array, np.array(range(len(array))) - 1.0, kind="next")(target))
            if index == -1:
                return 0, 0.0
            return index, target - array[index]
        return wrapped


class BezierCurve(CurveInterpolantBase):
    """
    Bezier curves defined on domain [0, 1].
    """
    def __init__(self, points: Vector2ArrayType):
        self._points_ = points
        super().__init__()

    @lazy_property_initializer
    def _points_() -> Vector2ArrayType:
        return np.array(())

    @lazy_property
    def _order_(cls, points: Vector2ArrayType) -> int:
        return len(points) - 1

    @lazy_property
    def _gamma_(cls, order: int, points: Vector2ArrayType) -> scipy.interpolate.BSpline:
        return scipy.interpolate.BSpline(
            t=np.append(np.zeros(order + 1), np.ones(order + 1)),
            c=points,
            k=order
        )

    @lazy_property
    def _a_samples_(cls, order: int) -> FloatArrayType:
        segments = 16 if order > 1 else 1
        return np.linspace(0.0, 1.0, segments + 1)

    @lazy_property
    def _l_samples_(cls, gamma: scipy.interpolate.BSpline, a_samples: FloatArrayType) -> FloatArrayType:
        p_samples = gamma(a_samples)
        segment_lengths = np.linalg.norm(p_samples[1:] - p_samples[:-1], axis=1)
        return np.insert(np.cumsum(segment_lengths), 0, 0.0)

    @lazy_property
    def _a_l_interp_(cls, a_samples: FloatArrayType, l_samples: FloatArrayType) -> scipy.interpolate.interp1d:
        return interp1d(a_samples, l_samples)

    @lazy_property
    def _l_a_interp_(cls, l_samples: FloatArrayType, a_samples: FloatArrayType) -> Callable[[Real], Real]:
        return interp1d(l_samples, a_samples)

    @lazy_property
    def _a_final_(cls) -> float:
        return 1.0

    @lazy_property
    def _l_final_(cls, a_l_interp: scipy.interpolate.interp1d, a_final: float) -> float:
        return a_l_interp(a_final)

    def a_to_p(self, a: Real) -> Vector2Type:
        return self._gamma_(a)

    def a_to_l(self, a: Real) -> float:
        return self._a_l_interp_(a)

    def l_to_a(self, l: Real) -> float:
        return self._l_a_interp_(l)

    def partial_by_a(self, a: Real):
        return BezierCurve(np.array([
            BezierCurve(self._points_[:n]).a_to_p(a)
            for n in range(1, self._order_ + 2)
        ]))

    def rise_order_to(self, new_order: int):
        new_points = self._points_
        for n in range(self._order_ + 1, new_order + 1):
            mat = np.zeros((n + 1, n))
            mat[(np.arange(n), np.arange(n))] = np.arange(n, 0, -1) / n
            mat[(np.arange(n) + 1, np.arange(n))] = np.arange(1, n + 1) / n
            new_points = mat @ new_points
        return BezierCurve(new_points)


class Contour(CurveInterpolant[BezierCurve]):
    """
    A list of chained Bezier curves
    """
    pass


class Contours(CurveInterpolant[Contour]):
    """
    A list of contours, either open or closed
    """
    pass


class Path(metaclass=LazyMeta):
    """
    A list of contours, either open or closed
    """
    def __init__(
        self,
        path: skia.Path | Contours | None = None
        #children: list[Contour] | None = None
    ):
        if isinstance(path, skia.Path):
            self._skia_path_ = path
        elif isinstance(path, Contours):
            self._skia_path_ = Path._get_skia_path_by_contours(path)
        elif path is None:
            pass
        else:
            raise ValueError(f"Unsupported path type: {type(path)}")

        #self._skia_path_ = skia_path
        #self._contours: Contours = Contours()
        #self.contours_require_updating: bool = True

    def __deepcopy__(self, memo=None):
        return Path(skia.Path(self._skia_path_))

    @classmethod
    def _get_contours_by_skia_path(cls, path: skia.Path) -> Contours:
        contours = []
        contour = []
        iterator = iter(path)
        verb, points = iterator.next()
        while verb != skia.Path.kDone_Verb:
            if verb == skia.Path.Verb.kMove_Verb:
                pass
            elif verb in (
                skia.Path.Verb.kLine_Verb,
                skia.Path.Verb.kQuad_Verb,
                skia.Path.Verb.kCubic_Verb
            ):
                contour.append(BezierCurve(np.array([
                    np.array(list(point)) for point in points
                ])))
            elif verb == skia.Path.Verb.kConic_Verb:
                # Approximate per conic curve with 8 quads
                quad_points = skia.Path.ConvertConicToQuads(*points, iterator.conicWeight(), 3)
                for i in range(0, len(quad_points), 2):
                    contour.append(BezierCurve(np.array([
                        np.array(list(point)) for point in quad_points[i:i + 3]
                    ])))
            elif verb == skia.Path.Verb.kClose_Verb:
                if contour:
                    contours.append(Contour(contour))
                    contour = []
            else:
                raise ValueError
            verb, points = iterator.next()
        if contour:
            contours.append(Contour(contour))
        return Contours(contours)

    @classmethod
    def _get_skia_path_by_contours(cls, contours: Contours) -> skia.Path:
        path = skia.Path()
        for contour in contours._children_:
            path.moveTo(*contour._children_[0]._points_[0])
            for curve in contour._children_:
                points = curve._points_
                len_points = len(points)
                if len_points == 2:
                    path.lineTo(*points[1])
                elif len_points == 3:
                    path.quadTo(*points[1], *points[2])
                elif len_points == 4:
                    path.cubicTo(*points[1], *points[2], *points[3])
                else:
                    raise ValueError
            path.close()
        return path

    @lazy_property_initializer
    def _skia_path_() -> skia.Path:
        return skia.Path()

    #@_skia_path.setter
    #def _skia_path(self, arg: skia.Path) -> None:
    #    pass

    @lazy_property
    def _contours_(cls, skia_path: skia.Path) -> Contours:
        return Path._get_contours_by_skia_path(skia_path)
        #if self.contours_require_updating:
        #    self._contours = self._get_contours_by_skia_path(self._skia_path_)
        #    self.contours_require_updating = False
        #return self._contours

    #def get_updated_children(self) -> list[Contour]:
    #    return self._get_contours_by_skia_path(self.skia_path)

    @_skia_path_.updater
    def move_to(self, point: Vector2Type):
        #self.contours_require_updating = True
        self._skia_path_.moveTo(skia.Point(*point))
        #self._skia_path = self._skia_path_
        return self

    @_skia_path_.updater
    def line_to(self, point: Vector2Type):
        #self.contours_require_updating = True
        self._skia_path_.lineTo(skia.Point(*point))
        #self._skia_path = self._skia_path_
        return self

    @_skia_path_.updater
    def quad_to(self, control_point: Vector2Type, point: Vector2Type):
        #self.contours_require_updating = True
        self._skia_path_.quadTo(skia.Point(*control_point), skia.Point(*point))
        #self._skia_path = self._skia_path_
        return self

    @_skia_path_.updater
    def cubic_to(self, control_point_0: Vector2Type, control_point_1: Vector2Type, point: Vector2Type):
        #self.contours_require_updating = True
        self._skia_path_.cubicTo(skia.Point(*control_point_0), skia.Point(*control_point_1), skia.Point(*point))
        #self._skia_path = self._skia_path_
        return self

    @_skia_path_.updater
    def conic_to(self, control_point: Vector2Type, point: Vector2Type, weight: Real):
        #self.contours_require_updating = True
        self._skia_path_.conicTo(skia.Point(*control_point), skia.Point(*point), weight)
        #self._skia_path = self._skia_path_
        return self

    @_skia_path_.updater
    def close_path(self):
        #self.contours_require_updating = True
        self._skia_path_.close()
        #self._skia_path = self._skia_path_
        return self

    @lazy_property
    def _a_final_(cls, contours: Contours) -> float:
        return contours._a_final_

    @lazy_property
    def _l_final_(cls, contours: Contours) -> float:
        return contours._l_final_

    def a_to_p(self, a: Real) -> Vector2Type:
        return self._contours_.a_to_p(a)

    def a_to_l(self, a: Real) -> float:
        return self._contours_.a_to_l(a)

    def l_to_a(self, l: Real) -> float:
        return self._contours_.l_to_a(l)

    def a_ratio_to_p(self, a_ratio: Real) -> Vector2Type:
        return self._contours_.a_ratio_to_p(a_ratio)

    def a_ratio_to_l_ratio(self, a_ratio: Real) -> float:
        return self._contours_.a_ratio_to_l_ratio(a_ratio)

    def l_ratio_to_a_ratio(self, l_ratio: Real) -> float:
        return self._contours_.l_ratio_to_a_ratio(l_ratio)

    def partial_by_a(self, a: Real):
        return Path(self._contours_.partial_by_a(a))

    def partial_by_l(self, l: Real):
        return Path(self._contours_.partial_by_l(l))

    def partial_by_a_ratio(self, a_ratio: Real):
        return Path(self._contours_.partial_by_a_ratio(a_ratio))

    def partial_by_l_ratio(self, l_ratio: Real):
        return Path(self._contours_.partial_by_l_ratio(l_ratio))
