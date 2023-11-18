from __future__ import annotations


from typing import Self

import moderngl

from ...lazy.lazy import Lazy
from .buffer import Buffer


class TextureBuffer(Buffer):
    __slots__ = ()

    def __init__(
        self: Self,
        *,
        name: str,
        # Note, each texture should occur only once.
        textures: moderngl.Texture | tuple[moderngl.Texture, ...],
        array_lens: dict[str, int] | None = None
    ) -> None:
        #replaced_field = re.sub(r"^sampler2D\b", "uint", field)
        #assert field != replaced_field
        if isinstance(textures, tuple):
            shape = (len(textures),)
        else:
            shape = ()
            textures = (textures,)
        super().__init__(
            #field=replaced_field,
            #structs=None,
            #shape=texture_array.shape,
            shape=shape,
            array_lens=array_lens
        )
        self._name_ = name
        self._textures_ = textures

    @Lazy.variable()
    @staticmethod
    def _name_() -> str:
        return ""

    @Lazy.variable(plural=True)
    @staticmethod
    def _textures_() -> tuple[moderngl.Texture, ...]:
        return ()
