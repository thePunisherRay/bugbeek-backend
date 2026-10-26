import json
import shlex
from urllib.parse import parse_qsl, urlsplit

_DATA_FLAGS = {"-d", "--data", "--data-raw", "--data-binary", "--data-ascii", "--data-urlencode"}


def parse_curl(command: str) -> dict:
    text = command.replace("\\\r\n", " ").replace("\\\n", " ")
    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        raise ValueError(f"Could not parse cURL command: {exc}")
    if not tokens or tokens[0] != "curl":
        raise ValueError("Command must start with 'curl'")

    method = url = data = None
    headers: dict[str, str] = {}
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        value = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok in ("-X", "--request") and value:
            method = value.upper(); i += 2
        elif tok in ("-H", "--header") and value:
            name, _, v = value.partition(":")
            headers[name.strip()] = v.strip(); i += 2
        elif tok in _DATA_FLAGS and value is not None:
            data = value; i += 2
        elif tok == "--json" and value is not None:
            data = value
            headers.setdefault("Content-Type", "application/json"); i += 2
        elif tok == "--url" and value:
            url = value; i += 2
        elif tok.startswith("-"):
            i += 1
        else:
            url = url or tok; i += 1

    if not url:
        raise ValueError("cURL command does not contain a URL")
    return {"method": method or ("POST" if data is not None else "GET"), "url": url, "headers": headers, "data": data}


def _infer_schema(value):
    if isinstance(value, dict):
        return {"type": "object", "properties": {k: _infer_schema(v) for k, v in value.items()}, "required": list(value)}
    if isinstance(value, list):
        return {"type": "array", "items": _infer_schema(value[0]) if value else {}}
    if isinstance(value, bool):
        return {"type": "boolean", "example": value}
    if isinstance(value, int):
        return {"type": "integer", "example": value}
    if isinstance(value, float):
        return {"type": "number", "example": value}
    if isinstance(value, str):
        return {"type": "string", "example": value}
    return {}


def curl_to_spec(command: str) -> dict:
    """Turn one cURL command into a minimal OpenAPI 3 document."""
    c = parse_curl(command)
    parts = urlsplit(c["url"])
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("cURL command must include a full http(s) URL")

    path = parts.path or "/"
    method = c["method"].lower()
    operation: dict = {
        "summary": f"{c['method']} {path}",
        "parameters": [
            {"name": k, "in": "query", "required": True, "schema": {"type": "string", "example": v}}
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
        ],
        "responses": {"200": {"description": "Successful response"}},
    }
    # Header names are kept; values (e.g. tokens) are deliberately not stored.
    for name in c["headers"]:
        if name.lower() != "content-type":
            operation["parameters"].append({"name": name, "in": "header", "required": True, "schema": {"type": "string"}})

    if c["data"] is not None:
        try:
            schema, ctype = _infer_schema(json.loads(c["data"])), "application/json"
        except ValueError:
            schema, ctype = {"type": "string"}, c["headers"].get("Content-Type", "text/plain")
        operation["requestBody"] = {"required": True, "content": {ctype: {"schema": schema}}}

    return {
        "openapi": "3.1.0",
        "info": {"title": parts.netloc, "version": "1.0.0"},
        "servers": [{"url": f"{parts.scheme}://{parts.netloc}"}],
        "paths": {path: {method: operation}},
    }
