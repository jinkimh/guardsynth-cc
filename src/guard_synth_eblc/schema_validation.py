"""Dependency-free validator for the JSON-Schema subset used by public EBLC v0.

It intentionally supports only the keywords present in ``schemas/*.json``.
Unsupported schema keywords fail closed so a fixture cannot silently bypass a
new constraint.
"""

from __future__ import annotations

import json
from math import isfinite
from pathlib import Path
from typing import Any


SUPPORTED = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "type",
    "required", "properties", "additionalProperties", "items", "enum", "const",
    "oneOf", "minimum", "minLength", "minItems", "maxItems",
}


class SchemaValidationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    def reject_nonfinite(token: str) -> None:
        raise SchemaValidationError(f"$: non-finite JSON number {token}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_nonfinite,
    )


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
        )
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _resolve_local_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise SchemaValidationError(f"$: only local JSON Schema refs are supported: {reference}")
    current: Any = root_schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise SchemaValidationError(f"$: unresolved JSON Schema ref {reference}")
        current = current[token]
    if not isinstance(current, dict):
        raise SchemaValidationError(f"$: JSON Schema ref is not an object: {reference}")
    return current


def validate(
    instance: Any,
    schema: dict[str, Any],
    path: str = "$",
    *,
    root_schema: dict[str, Any] | None = None,
) -> None:
    root = schema if root_schema is None else root_schema
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise SchemaValidationError(f"{path}: unsupported schema keywords {sorted(unknown)}")
    if "$ref" in schema:
        validate(instance, _resolve_local_ref(root, schema["$ref"]), path, root_schema=root)
        return
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            try:
                validate(instance, branch, path, root_schema=root)
            except SchemaValidationError:
                continue
            matches += 1
        if matches != 1:
            raise SchemaValidationError(f"{path}: expected exactly one oneOf match, got {matches}")
        return
    expected = schema.get("type")
    if expected is not None:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not any(_matches_type(instance, item) for item in expected_types):
            raise SchemaValidationError(f"{path}: expected type {expected_types}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value is outside enum")
    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"{path}: value does not match const")
    if isinstance(instance, str) and len(instance) < schema.get("minLength", 0):
        raise SchemaValidationError(f"{path}: string is too short")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"{path}: below minimum")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            raise SchemaValidationError(f"{path}: array is too short")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaValidationError(f"{path}: array is too long")
        if "items" in schema:
            for index, item in enumerate(instance):
                validate(item, schema["items"], f"{path}[{index}]", root_schema=root)
    if isinstance(instance, dict):
        for field in schema.get("required", []):
            if field not in instance:
                raise SchemaValidationError(f"{path}: missing required field {field}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = set(instance) - set(properties)
            if extras:
                raise SchemaValidationError(f"{path}: unexpected fields {sorted(extras)}")
        for key, subschema in properties.items():
            if key in instance:
                validate(instance[key], subschema, f"{path}.{key}", root_schema=root)


def validate_file(instance_path: Path, schema_path: Path) -> None:
    validate(load_json(instance_path), load_json(schema_path))
