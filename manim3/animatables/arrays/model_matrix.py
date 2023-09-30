import numpy as np

from ...constants.custom_typing import (
    NP_3f8,
    NP_44f8,
    NP_x3f8
)
from ...lazy.lazy import Lazy
from ...utils.space_utils import SpaceUtils
from .animatable_array import AnimatableArray


class ModelMatrix(AnimatableArray[NP_44f8]):
    __slots__ = ()

    @Lazy.variable(hasher=Lazy.array_hasher)
    @staticmethod
    def _array_() -> NP_44f8:
        return np.identity(4)

    @classmethod
    def _convert_input(
        cls,
        model_matrix_input: object
    ):
        raise ValueError("Cannot manually set the model matrix")

    def _apply_affine(
        self,
        vector: NP_3f8
    ) -> NP_3f8:
        return SpaceUtils.apply_affine(self._array_, vector)

    def _apply_affine_multiple(
        self,
        vectors: NP_x3f8
    ) -> NP_x3f8:
        return SpaceUtils.apply_affine(self._array_, vectors)