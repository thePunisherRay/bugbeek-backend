from typing import Any


class SchemaResolver:

    def __init__(self, specification: dict[str, Any]):
        self.specification = specification
        self.schemas = (
            specification
            .get("components", {})
            .get("schemas", {})
        )

    def resolve(self, schema: dict[str, Any] | None) -> dict[str, Any] | None:

        if not schema:
            return None

        if "$ref" in schema:
            reference = schema["$ref"]

            if not reference.startswith("#/"):
                return schema

            resolved = self._resolve_reference(reference)

            if resolved is None:
                return schema

            return resolved

        return schema

    def _resolve_reference(
        self,
        reference: str
    ) -> dict[str, Any] | None:

        parts = reference.lstrip("#/").split("/")

        current: Any = self.specification

        for part in parts:
            if not isinstance(current, dict):
                return None

            current = current.get(part)

            if current is None:
                return None

        return current