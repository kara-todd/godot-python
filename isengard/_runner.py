from typing import Any


class Runner:
    def __init__(self, rules_graph, workdir, dbpath):
        pass

    def run(self, name: str) -> Any:
        pass


# async def run(name: Edge, rules: List[Rule], workdir: Path, dbpath: Path) -> Any:
#     check_consistency(name, rules)

#     async def _run(name, rules, results, stack):
#         assert name not in stack
#         stack = {*stack, name}
#         rule = deps_map.get(name)
#         assert rule

#         inputs = []
#         for input in rule.inputs:
#             if isinstance(input, RuleItem):
#                 inputs.append(await _run(input.name, rules, results))
#             else:
#                 inputs.append(input.value)

#         if inspect.iscoroutinefunction(rule.fn):
#             results = await rule.fn(**inputs)
#         else:
#             results = rule.fn(**inputs)
#         assert len(results) == len(rule.outputs)
#         for result, output in zip(results, rule.outputs):
#             results[output.name] = result

#         return result[name]

#     results = {}
#     stack = set()
#     return _run(name, rules, results, stack)
