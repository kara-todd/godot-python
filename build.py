import sys
from pathlib import Path
from typing import Callable, Optional
import isengard


isg = isengard.Isengard(__file__, subdir_default_filename="BUILD.py")


@isg.lazy_config()
def release_format_ext(host_platform: str) -> str:
    # Zip format doesn't support symlinks that are needed for Linux&macOS
    if host_platform == "windows":
        return "zip"
    else:
        return "tar.bz2"


@isg.rule(output="{build_dir}/godot-python-{release_suffix}-{host_platform}.{release_format_ext}", input="{build_dir}/dist/")
def generate_release(output: Path, input: Path) -> None:
    for suffix, format in [(".zip", "zip"), (".tar.bz2", "bztar")]:
        if output.name.endswith(suffix):
            base_name = str(output)[: -len(suffix)]
            break

    from shutil import make_archive
    make_archive(base_name, format, root_dir=input.abspath)


libfoo = isg.cython_module("foo.pyx")
isg.install(libfoo)

pythonscript_pyx_src, pythonscript_pyx_header = isg.cython_to_c("_pythonscript.pyx")
pythonscript_lib = isg.shared_library("_pythonscript", ["pythonscript.c", pythonscript_pyx_src, pythonscript_pyx_header])
isg.install(pythonscript_lib)


def _customize_cflags(cflags, *args):
    return [[*cflags, "-O2"], *args]

isg.c("foo.c", config_hook=_customize_cflags)


@isg.meta_rule
def cython(source: str, config_hook: Optional[Callable]=None):
    name, ext = source.rsplit(".")
    if ext != "pyx":
        raise ValueError("Expects .pyx file as source")
    output = f"{name}.so"

    @isg.rule(output=f"{{__DST__}}/{name}.so", input=source)
    def _cython_rule(output: Path, input: Path, cflags: List[str], linkflags: List[str]):
        if config_hook:
            cflags, linkflags = config_hook(cflags, linkflags)
        pass

    return isengard.Rule(f"cythonize_{source}", outputs=[output], inputs=[source], fn=_cython)

@isg.meta_rule
def shared_library(libname, sources):
    def _shared_library():
        pass

    return _shared_library


isg.subdir("pythonscript")

if __name__ == "__main__":
    import sys
    isg.main(sys.argv)
