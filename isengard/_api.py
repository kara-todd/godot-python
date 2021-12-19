from contextvars import ContextVar
from pathlib import Path
from typing import Dict, List, Set, Callable, Union, Optional, Any, Union
import inspect

from ._graph import RulesGraph, Target, TargetLike, Rule, RuleFnSignature
from ._runner import Runner


MetaRuleFnSignature = Callable[..., Rule]

_parent: ContextVar["Isengard"] = ContextVar('context')

def get_parent() -> "Isengard":
    try:
        return _parent.get()
    except LookupError as exc:
        raise RuntimeError("Not in a subdir !") from exc


def extract_virtual_targets_from_signature(fn: Callable):
    targets: List[Target] = []
    signature = inspect.signature(fn)
    for param in signature.parameters.values():
        if not param.empty:
            raise TypeError(f"Rule `{fn}` cannot have default value to parameters")
        if not param.kind == param.VAR_POSITIONAL:
            raise TypeError(f"Rule `{fn}` cannot have *args parameter")
        if not param.kind == param.VAR_KEYWORD:
            raise TypeError(f"Rule `{fn}` cannot have **kwargs parameter")
        targets.append(Target(f"{param.value}@"))
    return targets


class Isengard:
    __slots__ = (
        "_entrypoint_name",
        "_subdir_default_filename",
        "_entrypoint_dir",
        "_workdir",
        "_db_path",
        "_rules_graph",
        "_meta_rules",
    )

    def __init__(self, self_file: Union[str, Path], db: Union[str, Path]=".isengard.sqlite", subdir_default_filename: Optional[str] = None):
        entrypoint_path = Path(self_file).absolute()
        self._subdir_default_filename = subdir_default_filename or entrypoint_path
        self._entrypoint_name = entrypoint_path.name
        self._entrypoint_dir = entrypoint_path.parent
        self._workdir = self._entrypoint_dir  # Modified when reading subdir

        if not isinstance(db, Path):
            db = Path(db)
        if not db.is_absolute():
            db = self._entrypoint_dir / db
        self._db_path = db

        self._rules_graph = RulesGraph()
        self._meta_rules: Dict[str, MetaRuleFnSignature] = {}

    def rule(self, outputs: Optional[List[TargetLike]]=None, output: Optional[TargetLike]=None, inputs: Optional[List[TargetLike]]=None, input: Optional[TargetLike]=None, name: Optional[str]=None):
        if output is not None:
            if outputs is not None:
                raise TypeError("Cannot define both `output` and `outputs` parameters")
            else:
                outputs = [output]
        elif outputs is None:
            raise TypeError("One of `output` or `outputs` parameters is mandatory")

        if input is not None:
            if inputs is not None:
                raise TypeError("Cannot define both `input` and `inputs` parameters")
            else:
                inputs = [input]
        elif inputs is None:
            inputs = []

        def wrapper(fn: RuleFnSignature) -> RuleFnSignature:
            all_outputs = [*outputs, *extract_virtual_targets_from_signature(fn)]
            rule = Rule(name=name or fn.__name__, outputs=all_outputs, inputs=inputs, fn=fn)
            self._rules_graph.add(rule)
            return fn

        return wrapper

    def meta_rule(self, fn: MetaRuleFnSignature) -> MetaRuleFnSignature:
        try:
            existing = self._meta_rules[fn.__name__]
            raise RuntimeError(f"Meta-rule {fn.__name__} already exists ({existing})")
        except KeyError:
            self._meta_rules[fn.__name__] = fn
        return fn

    def __getattr__(self, name):
        try:
            return self._meta_rules[name]
        except KeyError as exc:
            raise AttributeError(f"No meta rule named `{name}`") from exc

    def clone(self):
        raise NotImplementedError("TODO !")

    def subdir(self, subdir: str, filename: Optional[str] = None) -> None:
        token = _parent.set(self)
        previous_workdir = self._workdir
        try:
            # Temporary self modification is not a very clean approach
            # but at least it's fast&simple ;-)
            self._workdir = self._workdir / subdir
            subscript_path = self._workdir / (filename or self._subdir_default_filename)
            exec(subscript_path.read_text())
        finally:
            self._workdir = previous_workdir
            _parent.reset(token)

    def run(self, name: str) -> Any:
        runner = Runner(self._rules_graph, self._workdir, self._db_path)
        return runner.run(name)

    def main(self, argv: str) -> Any:
        self.run(argv[1])
