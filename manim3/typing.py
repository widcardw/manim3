from typing import Any, Literal, Union

import numpy as np


__all__ = [
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
    "TextureArrayType",
    #"UniformType",
    "AttributeType",
    #"AttributesItemType",
    #"AttributesDictType",
    "VertexIndicesType",
    "Self"
]


_ND = int
_2D = Literal[2]
_3D = Literal[3]
_4D = Literal[4]

Vector2Type = np.ndarray[tuple[_2D], np.dtype[np.float64]]
Vector3Type = np.ndarray[tuple[_3D], np.dtype[np.float64]]
Vector4Type = np.ndarray[tuple[_4D], np.dtype[np.float64]]
Matrix33Type = np.ndarray[tuple[_3D, _3D], np.dtype[np.float64]]
Matrix44Type = np.ndarray[tuple[_4D, _4D], np.dtype[np.float64]]

FloatArrayType = np.ndarray[tuple[_ND], np.dtype[np.float64]]
Vector2ArrayType = np.ndarray[tuple[_ND, _2D], np.dtype[np.float64]]
Vector3ArrayType = np.ndarray[tuple[_ND, _3D], np.dtype[np.float64]]
Vector4ArrayType = np.ndarray[tuple[_ND, _4D], np.dtype[np.float64]]
Matrix33ArrayType = np.ndarray[tuple[_ND, _3D, _3D], np.dtype[np.float64]]
Matrix44ArrayType = np.ndarray[tuple[_ND, _4D, _4D], np.dtype[np.float64]]

ColorArrayType = Vector4Type
TextureArrayType = np.ndarray[tuple[_ND, _ND, _3D | _4D], np.dtype[np.uint8]]
#UniformType = Union[
#    int,
#    float,
#    Vector2Type,
#    Vector3Type,
#    Vector4Type,
#    Matrix33Type,
#    Matrix44Type
#]
AttributeType = Union[
    FloatArrayType,
    Vector2ArrayType,
    Vector3ArrayType,
    Vector4ArrayType,
    Matrix33ArrayType,
    Matrix44ArrayType
]
#AttributesType = np.ndarray[tuple[int], np.dtype[Any]]
#AttributesItemType = np.ndarray[tuple[int], np.dtype[Any]]
#AttributesDictType = dict[AttributeUsage, AttributesItemType]
VertexIndicesType = np.ndarray[tuple[_ND], np.dtype[np.int32]]

Self = Any  # This shall be removed when advanced to py 3.11