from dataclasses import dataclass
import re
import os

import moderngl

from .constants import MANIM3_PATH
from .typing import *


@dataclass
class ShaderData:
    enable_depth_test: bool
    enable_blend: bool
    cull_face: str
    wireframe: bool
    shader_filename: str
    define_macros: list[str]
    textures_dict: dict[str, tuple[TextureArrayType, int]]
    #uniforms_dict: dict[str, UniformType]
    attributes_dict: dict[str, tuple[AttributeType, str]]
    vertex_indices: VertexIndicesType
    render_primitive: int


class ContextWrapper:
    _GLSL_FILE_CACHE: dict[str, str] = {}

    def __init__(self: Self, ctx: moderngl.Context):
        self._ctx = ctx

    @classmethod
    def _read_glsl_file(cls, filename: str) -> str:
        if filename in cls._GLSL_FILE_CACHE:
            return cls._GLSL_FILE_CACHE[filename]
        with open(os.path.join(MANIM3_PATH, "shaders", f"{filename}.glsl")) as f:
            result = f.read()
        cls._GLSL_FILE_CACHE[filename] = result
        return result

    @classmethod
    def _insert_defines(cls, content: str, define_macros: list[str]):
        version_str, rest = content.split("\n", 1)
        return "\n".join([
            version_str,
            *[
                f"#define {define_macro}"
                for define_macro in define_macros
            ],
            rest
        ])

    @classmethod
    def _get_program(
        cls,
        ctx: moderngl.Context,
        shader_filename: str,
        define_macros: list[str]
    ) -> moderngl.Program:
        content = cls._insert_defines(cls._read_glsl_file(shader_filename), define_macros)
        shaders_dict = dict.fromkeys((
            "VERTEX_SHADER",
            "FRAGMENT_SHADER",
            "GEOMETRY_SHADER",
            "TESS_CONTROL_SHADER",
            "TESS_EVALUATION_SHADER"
        ))
        for shader_type in shaders_dict:
            if re.search(f"\\b{shader_type}\\b", content):
                shaders_dict[shader_type] = cls._insert_defines(content, [shader_type])
        if shaders_dict["VERTEX_SHADER"] is None:
            raise
        program = ctx.program(
            vertex_shader=shaders_dict["VERTEX_SHADER"],
            fragment_shader=shaders_dict["FRAGMENT_SHADER"],
            geometry_shader=shaders_dict["GEOMETRY_SHADER"],
            tess_control_shader=shaders_dict["TESS_CONTROL_SHADER"],
            tess_evaluation_shader=shaders_dict["TESS_EVALUATION_SHADER"]
        )
        return program

    @classmethod
    def _get_vao(
        cls,
        ctx: moderngl.Context,
        program: moderngl.Program,
        textures_dict: dict[str, tuple[TextureArrayType, int]],
        #uniforms_dict: dict[str, UniformType],
        attributes_dict: dict[str, tuple[AttributeType, str]],
        vertex_indices: VertexIndicesType,
        render_primitive: int
    ) -> moderngl.VertexArray:
        #for uniform_name, uniform_val in uniforms_dict.items():
        #    uniform = program[uniform_name]
        #    if not isinstance(uniform, moderngl.Uniform):
        #        continue
        #    if not isinstance(uniform_val, (int, float)):
        #        uniform_val = tuple(uniform_val.flatten())
        #    uniform.__setattr__("value", uniform_val)

        for name, (texture_array, location) in textures_dict.items():
            uniform = program[name]
            if not isinstance(uniform, moderngl.Uniform):
                continue
            uniform.__setattr__("value", location)
            shape = texture_array.shape
            texture = ctx.texture(
                size=shape[:2],
                components=shape[2],
                data=texture_array.tobytes(),
            )
            texture.use(location=location)

        content = [
            (ctx.buffer(array.tobytes()), buffer_format, name)
            for name, (array, buffer_format) in attributes_dict.items()
        ]
        ibo = ctx.buffer(vertex_indices.tobytes())
        vao = ctx.vertex_array(
            program=program,
            content=content,
            index_buffer=ibo,
            index_element_size=4,
            mode=render_primitive
        )
        return vao

    @classmethod
    def _configure_context(
        cls,
        ctx: moderngl.Context,
        enable_depth_test: bool,
        enable_blend: bool,
        cull_face: str,
        wireframe: bool
    ) -> None:
        if enable_depth_test:
            ctx.enable(moderngl.DEPTH_TEST)
        else:
            ctx.disable(moderngl.DEPTH_TEST)
        if enable_blend:
            ctx.enable(moderngl.BLEND)
        else:
            ctx.disable(moderngl.BLEND)
        ctx.cull_face = cull_face
        ctx.wireframe = wireframe

    def render(self: Self, shader_data: ShaderData) -> None:
        ctx = self._ctx
        self._configure_context(
            ctx,
            shader_data.enable_depth_test,
            shader_data.enable_blend,
            shader_data.cull_face,
            shader_data.wireframe
        )
        program = self._get_program(
            ctx,
            shader_data.shader_filename,
            shader_data.define_macros
        )
        vao = self._get_vao(
            ctx,
            program,
            shader_data.textures_dict,
            #shader_data.uniforms_dict,
            shader_data.attributes_dict,
            shader_data.vertex_indices,
            shader_data.render_primitive
        )
        vao.render()