__all__ = [
    "Real",
    "Vector2Type",
    "Vector3Type",
    "Vector4Type",
    "Matrix33Type",
    "Matrix44Type",
    "FloatArrayType",
    "Vector2ArrayType",
    "Vector3ArrayType",
    "Vector4ArrayType",
    "Matrix33ArrayType",
    "Matrix44ArrayType",
    "ColorArrayType",
    #"AttributeType",
    #"UniformType",
    "VertexIndicesType",
    "ColorType",
    "Span",
    "Selector"
]


from colour import Color
import re
from typing import Iterable, Literal, Union

import numpy as np


Real = float | int

_ND = int
_2D = Literal[2]
_3D = Literal[3]
_4D = Literal[4]

Vector2Type = np.ndarray[tuple[_2D], np.dtype[np.float32]]
Vector3Type = np.ndarray[tuple[_3D], np.dtype[np.float32]]
Vector4Type = np.ndarray[tuple[_4D], np.dtype[np.float32]]
Matrix33Type = np.ndarray[tuple[_3D, _3D], np.dtype[np.float32]]
Matrix44Type = np.ndarray[tuple[_4D, _4D], np.dtype[np.float32]]

FloatArrayType = np.ndarray[tuple[_ND], np.dtype[np.float32]]
Vector2ArrayType = np.ndarray[tuple[_ND, _2D], np.dtype[np.float32]]
Vector3ArrayType = np.ndarray[tuple[_ND, _3D], np.dtype[np.float32]]
Vector4ArrayType = np.ndarray[tuple[_ND, _4D], np.dtype[np.float32]]
Matrix33ArrayType = np.ndarray[tuple[_ND, _3D, _3D], np.dtype[np.float32]]
Matrix44ArrayType = np.ndarray[tuple[_ND, _4D, _4D], np.dtype[np.float32]]

ColorArrayType = Vector4Type
#AttributeType = Union[
#    FloatArrayType,
#    Vector2ArrayType,
#    Vector3ArrayType,
#    Vector4ArrayType,
#    Matrix33ArrayType,
#    Matrix44ArrayType
#]
#UniformType = Union[
#    bool,
#    int,
#    float,
#    Vector2Type,
#    Vector3Type,
#    Vector4Type,
#    Matrix33Type,
#    Matrix44Type
#]
VertexIndicesType = np.ndarray[tuple[_ND], np.dtype[np.int32]]

ColorType = Color | str
Span = tuple[int, int]
Selector = Union[
    str,
    re.Pattern,
    tuple[Union[int, None], Union[int, None]],
    Iterable[Union[
        str,
        re.Pattern,
        tuple[Union[int, None], Union[int, None]]
    ]]
]
