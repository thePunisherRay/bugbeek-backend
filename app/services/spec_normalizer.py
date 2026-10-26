import re
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _lookup(spec: dict, ref: str) -> Any:
    current: Any = spec
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def dereference(spec: dict) -> dict:
    """Return a copy of the spec with every local $ref inlined.

    Recursive references are cut off with a placeholder object so the walk
    always terminates.
    """

    def walk(node: Any, stack: tuple) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/"):
                if ref in stack:
                    return {"type": "object", "description": f"Recursive reference to {ref.split('/')[-1]}"}
                target = _lookup(spec, ref)
                return node if target is None else walk(target, stack + (ref,))
            return {k: walk(v, stack) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(item, stack) for item in node]
        return node

    return walk(spec, ())


def ensure_operation_ids(spec: dict) -> None:
    """Give every operation a unique operationId (the UI groups tests by it)."""
    seen: set[str] = set()
    for path, item in spec.get("paths", {}).items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            op_id = operation.get("operationId") or (
                f"{method.lower()}_{re.sub(r'[^a-zA-Z0-9]+', '_', path).strip('_') or 'root'}"
            )
            base, n = op_id, 2
            while op_id in seen:
                op_id, n = f"{base}_{n}", n + 1
            seen.add(op_id)
            operation["operationId"] = op_id
