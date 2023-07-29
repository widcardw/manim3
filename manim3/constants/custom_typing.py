__all__ = (
    "NP_f8",
    "NP_2f8",
    "NP_3f8",
    "NP_4f8",
    "NP_33f8",
    "NP_44f8",
    "NP_xf8",
    "NP_x2f8",
    "NP_x3f8",
    "NP_x4f8",
    "NP_x33f8",
    "NP_x44f8",
    "NP_i4",
    "NP_xi4",
    "NP_x2i4",
    "NP_x3i4",
    "NP_xxi4",
    "ColorT",
    "AlignmentT",
    "SelectorT"
)


import re
from typing import Literal

import numpy as np
from colour import Color


_XD = int
_2D = Literal[2]
_3D = Literal[3]
_4D = Literal[4]

NP_f8 = np.ndarray[tuple[()], np.dtype[np.float64]]
NP_2f8 = np.ndarray[tuple[_2D], np.dtype[np.float64]]
NP_3f8 = np.ndarray[tuple[_3D], np.dtype[np.float64]]
NP_4f8 = np.ndarray[tuple[_4D], np.dtype[np.float64]]
NP_33f8 = np.ndarray[tuple[_3D, _3D], np.dtype[np.float64]]
NP_44f8 = np.ndarray[tuple[_4D, _4D], np.dtype[np.float64]]
NP_xf8 = np.ndarray[tuple[_XD], np.dtype[np.float64]]
NP_x2f8 = np.ndarray[tuple[_XD, _2D], np.dtype[np.float64]]
NP_x3f8 = np.ndarray[tuple[_XD, _3D], np.dtype[np.float64]]
NP_x4f8 = np.ndarray[tuple[_XD, _4D], np.dtype[np.float64]]
NP_x33f8 = np.ndarray[tuple[_XD, _3D, _3D], np.dtype[np.float64]]
NP_x44f8 = np.ndarray[tuple[_XD, _4D, _4D], np.dtype[np.float64]]

NP_i4 = np.ndarray[tuple[()], np.dtype[np.int32]]
NP_xi4 = np.ndarray[tuple[_XD], np.dtype[np.int32]]
NP_x2i4 = np.ndarray[tuple[_XD, _2D], np.dtype[np.int32]]
NP_x3i4 = np.ndarray[tuple[_XD, _3D], np.dtype[np.int32]]
NP_xxi4 = np.ndarray[tuple[_XD, _XD], np.dtype[np.int32]]

ColorT = Color | str | NP_3f8
AlignmentT = Literal["left", "center", "right"]
SelectorT = str | re.Pattern[str] | tuple[int, int]  # Slice is hashable in future versions.