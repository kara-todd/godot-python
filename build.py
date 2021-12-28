import sys
from pathlib import Path
from typing import Callable, Optional
import isengard


# class IsengardCMixin:
#     def shared_library(self, name: str, sources: List[str], extra_cflags=None, extra_linkflags=None):
#         for source in sources:
#             assert sources.endswith()
#         @self.rule()
#         def _shared_library():
#             pass

# clang -o build/x11-64/pythonscript/pythonscript.os -c -O2 -m64 -I/home/emmanuel/projects/godot/godot-python/build/x11-64/platforms/x11-64/cpython_build/include/python3.8/ -Werror-implicit-function-declaration -fcolor-diagnostics -fPIC -Igodot_headers build/x11-64/pythonscript/pythonscript.c
# clang -o build/x11-64/pythonscript/libpythonscript.so -m64 -L/home/emmanuel/projects/godot/godot-python/build/x11-64/platforms/x11-64/cpython_build/lib -Wl,-rpath,'$ORIGIN/lib' -shared build/x11-64/pythonscript/pythonscript.os -lpython3.8


# class IsengardCythonMixin:
#     pass


# class CustomizedIsengard(isengard.Isengard, IsengardCMixin, IsengardCythonMixin):
#     pass


# isg = CustomizedIsengard(__file__, subdir_default_filename="BUILD.py")
isg = isengard.Isengard(__file__, subdir_default_filename="BUILD.py")


# @isg.lazy_config()
# def release_format_ext(host_platform: str) -> str:
#     # Zip format doesn't support symlinks that are needed for Linux&macOS
#     if host_platform == "windows":
#         return "zip"
#     else:
#         return "tar.bz2"


# @isg.rule(output="{build_dir}/godot-python-{release_suffix}-{host_platform}.{release_format_ext}", input="{build_dir}/dist/")
# def generate_release(output: Path, input: Path) -> None:
#     for suffix, format in [(".zip", "zip"), (".tar.bz2", "bztar")]:
#         if output.name.endswith(suffix):
#             base_name = str(output)[: -len(suffix)]
#             break

#     from shutil import make_archive
#     make_archive(base_name, format, root_dir=input)


# libfoo = isg.cython_module("foo.pyx")
# isg.install(libfoo)

# pythonscript_pyx_src, pythonscript_pyx_header = isg.cython_to_c("_pythonscript.pyx")
# pythonscript_lib = isg.shared_library("_pythonscript", ["pythonscript.c", pythonscript_pyx_src, pythonscript_pyx_header])
# isg.install(pythonscript_lib)


# def _customize_cflags(cflags, *args):
#     return [[*cflags, "-O2"], *args]

# isg.c("foo.c", config_hook=_customize_cflags)


# @isg.meta_rule
# def cython(source: str, config_hook: Optional[Callable]=None):
#     name, ext = source.rsplit(".")
#     if ext != "pyx":
#         raise ValueError("Expects .pyx file as source")
#     output = f"{name}.so"

#     @isg.rule(output=f"{{__DST__}}/{name}.so", input=source)
#     def _cython_rule(output: Path, input: Path, cflags: List[str], linkflags: List[str]):
#         if config_hook:
#             cflags, linkflags = config_hook(cflags, linkflags)
#         pass

#     return isengard.Rule(f"cythonize_{source}", outputs=[output], inputs=[source], fn=_cython)

# @isg.meta_rule
# def shared_library(libname, sources):
#     def _shared_library():
#         pass

#     return _shared_library


isg.subdir("pythonscript")


@isg.lazy_config
def build_dir(basedir):
    build_dir = basedir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    return build_dir


if __name__ == "__main__":
    import platform

    build_platform = platform.system()
    host_platform = build_platform  # TODO: should be a parameter !
    isg.configure(
        build_platform=build_platform,
        host_platform=host_platform,

        cc="clang",
        cflags=(
            "-O2",
            "-m64",
            "-Werror-implicit-function-declaration",
            "-fcolor-diagnostics",
        ),
        godot_headers=isg.basedir / "godot_headers",
        python_headers=isg.basedir
        / "build/x11-64/platforms/x11-64/cpython_build/include/python3.8/",  # TODO: Lazy config ?
    )

    isg.run(isg.basedir / "build/Linux/pythonscript/pytonscript.os")
