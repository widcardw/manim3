from __future__ import annotations


import pathlib
import sys
from types import TracebackType
from typing import Self

import attrs
from colour import Color

from ..constants.custom_typing import (
    AlignmentType,
    ColorType
)
from .toplevel import Toplevel


@attrs.frozen(kw_only=True)
class Config:
    #write_video: bool = False
    #write_last_frame: bool = False
    #preview: bool = True
    gl_version: tuple[int, int] = (4, 3)
    fps: int = 30
    aspect_ratio: float = 16.0 / 9.0
    frame_height: float = 8.0
    pixel_height: int = 1080
    window_pixel_height: int = 540

    camera_distance: float = 5.0
    camera_near: float = 0.1
    camera_far: float = 100.0

    default_color: ColorType = Color("white")
    default_opacity: float = 1.0
    default_weight: float = 1.0
    background_color: ColorType = Color("black")
    background_opacity: float = 0.0
    mesh_ambient_strength: float = 1.0
    mesh_specular_strength: float = 0.5
    mesh_shininess: float = 32.0
    graph_width: float = 0.05

    latex_font_size: float = 30
    tex_alignment: AlignmentType = "left"
    tex_compiler: str = "xelatex"
    tex_preambles: tuple[str, ...] = (
        "\\usepackage[UTF8]{ctex}",
        "\\usepackage{amsmath}",
        "\\usepackage{amssymb}",
        "\\usepackage{xcolor}"  # Required for labelling.
    )
    math_tex_inline: bool = False
    # See `https://docs.mathjax.org/en/latest/input/tex/extensions/index.html`.
    mathjax_extensions: tuple[str, ...] = (
        "ams",
        "autoload",
        "base",
        "color",  # Required for labelling.
        "newcommand",
        "require"
    )
    mathjax_inline: bool = False

    pango_font_size: float = 30
    pango_alignment: AlignmentType = "left"
    pango_font: str = "Consolas"
    pango_justify: bool = False
    pango_indent: float = 0.0
    pango_line_width: float = -1.0
    code_font: str = "JetBrains Mono"
    code_language_suffix: str = ".py"

    shader_search_dirs: tuple[pathlib.Path, ...] = (
        pathlib.Path(),
        pathlib.Path(__import__("manim3").__file__).parent.joinpath("shaders")
    )
    image_search_dirs: tuple[pathlib.Path, ...] = (
        pathlib.Path(),
    )
    output_dir: pathlib.Path = pathlib.Path("manim3_output")
    video_output_dir: pathlib.Path = pathlib.Path("manim3_output/videos")
    image_output_dir: pathlib.Path = pathlib.Path("manim3_output/images")
    default_filename: str = sys.argv[0]

    @property
    def gl_version_code(
        self: Self
    ) -> int:
        major_version, minor_version = self.gl_version
        return major_version * 100 + minor_version * 10

    @property
    def frame_width(
        self: Self
    ) -> float:
        return self.aspect_ratio * self.frame_height

    @property
    def frame_size(
        self: Self
    ) -> tuple[float, float]:
        return self.frame_width, self.frame_height

    @property
    def frame_radii(
        self: Self
    ) -> tuple[float, float]:
        return self.frame_width / 2.0, self.frame_height / 2.0

    @property
    def pixel_width(
        self: Self
    ) -> int:
        return int(self.aspect_ratio * self.pixel_height)

    @property
    def pixel_size(
        self: Self
    ) -> tuple[int, int]:
        return self.pixel_width, self.pixel_height

    @property
    def pixel_per_unit(
        self: Self
    ) -> int:
        return int(self.pixel_height / self.frame_height)

    @property
    def window_pixel_width(
        self: Self
    ) -> int:
        return int(self.aspect_ratio * self.window_pixel_height)

    @property
    def window_pixel_size(
        self: Self
    ) -> tuple[int, int]:
        return self.window_pixel_width, self.window_pixel_height

    def __enter__(
        self: Self
    ) -> None:
        #assert Toplevel._configure_contextmanager is None
        #configure_contextmanager = Toplevel._configure()
        #Toplevel._configure_contextmanager = configure_contextmanager
        #configure_contextmanager.__enter__()
        Toplevel._config = self

    def __exit__(
        self: Self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None
    ) -> None:
        Toplevel._config = None
        #assert Toplevel._configure_contextmanager is not None
        #configure_contextmanager = Toplevel._configure_contextmanager
        #Toplevel._configure_contextmanager = None
        #configure_contextmanager.__exit__(exc_type, exc_value, exc_traceback)
