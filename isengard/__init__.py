from contextvars import ContextVar
import subprocess
from pathlib import Path, PurePath
from typing import Dict, List, Set, Tuple, Callable, Union, Optional, Any, Union, TypeVar
import inspect


C = TypeVar("C", bound=Callable[..., None])
_RESERVED_CONFIG_NAMES = {"output", "output", "inputs", "input", "basedir"}


class Target:
    __slots__ = ("workdir", "unresolved")

    def __init__(self, workdir, unresolved):
        self.workdir = workdir
        self.unresolved = unresolved

    def resolve(self, config) -> Path:
        try:
            resolved = Path(self.unresolved.format(**config))
        except KeyError as exc:
            raise ValueError(f"Unknown config `{exc.args[0]}`")
        if resolved.is_absolute():
            return resolved
        else:
            return self.workdir / resolved


TargetLike = Union[str, Target]


_parent: ContextVar["Isengard"] = ContextVar("context")


def get_parent() -> "Isengard":
    try:
        return _parent.get()
    except LookupError as exc:
        raise RuntimeError("Not in a subdir !") from exc


def extract_config_from_signature(fn: Callable) -> Set[str]:
    config = set()
    signature = inspect.signature(fn)
    for param in signature.parameters.values():
        if not param.empty:
            raise TypeError(f"Default value to parameters not allowed")
        if param.kind == param.VAR_POSITIONAL:
            raise TypeError(f"*args parameter not allowed")
        if param.kind == param.VAR_KEYWORD:
            raise TypeError(f"**kwargs parameter not allowed")
        config.add(param.name)
    return config


class Isengard:
    def __init__(
        self,
        self_file: Union[str, Path],
        db: Union[str, Path] = ".isengard.sqlite",
        subdir_default_filename: Optional[str] = None,
    ):
        entrypoint_path = Path(self_file).absolute()
        self._subdir_default_filename = subdir_default_filename or entrypoint_path
        self._entrypoint_name = entrypoint_path.name
        self._entrypoint_dir = entrypoint_path.parent
        self._workdir = self._entrypoint_dir  # Modified when reading subdir
        # TODO: allow other types in configuration ?
        self._config: Optional[Dict[str, Union[str, Path, Tuple[Union[str, Path]]]]] = None

        if not isinstance(db, Path):
            db = Path(db)
        if not db.is_absolute():
            db = self._entrypoint_dir / db
        self._db_path = db

        self._rules = []
        self._resolved_rules = []
        self._lazy_configs = []
        # self._rules_graph = RulesGraph()
        # self._meta_rules: Dict[str, MetaRuleFnSignature] = {}

    def subdir(self, subdir: str, filename: Optional[str] = None) -> None:
        previous_workdir = self._workdir
        token = _parent.set(self)
        try:
            # Temporary self modification is not a very clean approach
            # but at least it's fast&simple ;-)
            self._workdir /= subdir
            subscript_path = self._workdir / (filename or self._subdir_default_filename)
            code = compile(subscript_path.read_text(), subscript_path, "exec")
            exec(code)
        finally:
            self._workdir = previous_workdir
            _parent.reset(token)

    @property
    def basedir(self):
        return self._entrypoint_dir

    def configure(self, **config):
        """
        Note passing configuration as function arguments limit the name you can use
        (e.g. `compiler.c.flags` is not a valid name). This is intended to work
        well with dependency injection in the rule where configuration is requested
        by using it name as function argument.
        """
        for k, v in config.items():
            if isinstance(v, (str, Path)):
                continue
            elif isinstance(v, tuple):
                for x in v:
                    if not isinstance(x, (str, Path)):
                        break
                else:
                    continue
            raise ValueError(
                f"Invalid configuration `{k}`: value must be a str/Path or a tuple of str/Path"
            )
        invalid_config_names = config.keys() & _RESERVED_CONFIG_NAMES
        if invalid_config_names:
            raise ValueError(f"Reserved config name(s): {', '.join(invalid_config_names)}")
        config["basedir"] = self.basedir

        to_run = self._lazy_configs
        cannot_run_yet = []
        while to_run:
            for fn in to_run:
                kwargs = {}
                for k in extract_config_from_signature(fn):
                    try:
                        kwargs[k] = config[k]
                    except KeyError:
                        cannot_run_yet.append(fn)
                        break
                else:
                    config[fn.__name__] = fn(**kwargs)

            if to_run == cannot_run_yet:
                # Unknown config or recursive dependency between two lazy configs
                errors = []
                for fn in cannot_run_yet:
                    for missing in extract_config_from_signature(fn) - config.keys():
                        errors.append(f"Unknown `{missing}` needed by `{fn.__name__}`")
                raise RuntimeError(f"Invalid lazy config: {', '.join(errors)}")
            else:
                to_run = cannot_run_yet
                cannot_run_yet = []

        self._config = config
        for name, needed_config, outputs, inputs, fn in self._rules:
            try:
                self._resolved_rules.append(
                    (
                        name,
                        needed_config,
                        [x.resolve(config) for x in outputs],
                        [x.resolve(config) for x in inputs],
                        fn
                    )
                )
            except ValueError as exc:
                raise ValueError(f"Invalid rule `{name}`: {exc.args[0]}") from exc

    def lazy_config(self, fn):
        if self._config is not None:
            raise RuntimeError("Cannot create new lazy config once configure has been called !")

        self._lazy_configs.append(fn)

    def rule(self,
        outputs: Optional[List[TargetLike]]=None,
        output: Optional[TargetLike]=None,
        inputs: Optional[List[TargetLike]]=None,
        input: Optional[TargetLike]=None,
        name: Optional[str]=None
    ) -> Callable[[C], C]:
        if self._config is not None:
            raise RuntimeError("Cannot create new rules once configure has been called !")

        def wrapper(fn: C) -> C:
            nonlocal outputs, inputs
            needed_config = extract_config_from_signature(fn)

            if output is not None:
                if outputs is not None:
                    raise TypeError("Cannot define both `output` and `outputs` parameters")
                else:
                    outputs = [output]
                if "output" not in needed_config or "outputs" in needed_config:
                    raise TypeError("Function must have a `output` and no `outputs` parameter")
            elif outputs is not None:
                if "outputs" not in needed_config or "output" in needed_config:
                    raise TypeError("Function must have a `outputs` and no `output` parameter")
            else:
                raise TypeError("One of `output` or `outputs` parameters is mandatory")

            if input is not None:
                if inputs is not None:
                    raise TypeError("Cannot define both `input` and `inputs` parameters")
                else:
                    inputs = [input]
                if "input" not in needed_config or "inputs" in needed_config:
                    raise TypeError("Function must have an `input` and no `inputs` parameter")
            elif inputs is not None:
                if "inputs" not in needed_config or "input" in needed_config:
                    raise TypeError("Function must have an `inputs` and no `input` parameter")
            else:
                inputs = []

            # TODO: better check target format here ?
            outputs = [Target(self._workdir, x) for x in outputs]
            inputs = [Target(self._workdir, x) for x in inputs]

            self._rules.append((name or fn.__name__, needed_config, outputs, inputs, fn))
            return fn

        return wrapper

    def run(self, target: Path) -> None:
        if self._config is None:
            raise RuntimeError("Must call configure before !")

        target = target.absolute()
        for rule in self._resolved_rules:
            name, needed_config, outputs, inputs, fn = rule
            if target not in outputs:
                continue
            kwargs = {}
            for k in needed_config:
                if k == "output":
                    kwargs["output"] = outputs[0]
                elif k == "outputs":
                    kwargs["outputs"] = outputs
                elif k == "input":
                    kwargs["input"] = inputs[0]
                elif k == "inputs":
                    kwargs["inputs"] = inputs
                else:
                    kwargs[k] = self._config[k]
            fn(**kwargs)

        else:
            raise ValueError("Not rule has this target as output")

        # runner = Runner(self._rules_graph, self._workdir, self._db_path)
        # return runner.run(name)

    # def main(self, argv: str) -> Any:
    #     self.run(argv[1])
