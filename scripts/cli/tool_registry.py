"""Injectable, provider-neutral registry for conversation tools.

tags: [harness, cli, tools, registry, conversation]
routing_hints: [tools, tool-registry, conversation]
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable


ToolHandler = Callable[[dict[str, Any]], Any]
_TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SCHEMA_ANNOTATIONS = {
    "$id",
    "$schema",
    "default",
    "deprecated",
    "description",
    "examples",
    "readOnly",
    "title",
    "writeOnly",
}
_SCHEMA_VALIDATORS = {
    "additionalProperties",
    "const",
    "enum",
    "items",
    "maximum",
    "maxLength",
    "minimum",
    "minLength",
    "pattern",
    "properties",
    "required",
    "type",
}
_SCHEMA_TYPES = {"array", "boolean", "integer", "null", "number", "object", "string"}


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


@dataclass(frozen=True)
class ToolOutcome:
    result: Any = None
    error: str | None = None


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _validate_value(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if isinstance(expected, str) and not _matches_type(value, expected):
        raise ValueError(f"{path} must be {expected}")
    if isinstance(expected, list) and not any(
        isinstance(kind, str) and _matches_type(value, kind) for kind in expected
    ):
        raise ValueError(f"{path} has the wrong type")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path} does not match the required value")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} is not an allowed value")

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    raise ValueError(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        properties = properties if isinstance(properties, dict) else {}
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            child_schema = properties.get(key)
            if child_schema is None:
                if additional is False:
                    raise ValueError(f"{path}.{key} is not allowed")
                if isinstance(additional, dict):
                    _validate_value(child, additional, f"{path}.{key}")
            elif isinstance(child_schema, dict):
                _validate_value(child, child_schema, f"{path}.{key}")

    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, child in enumerate(value):
            _validate_value(child, schema["items"], f"{path}[{index}]")

    if isinstance(value, str):
        if isinstance(schema.get("minLength"), int) and len(value) < schema["minLength"]:
            raise ValueError(f"{path} is shorter than allowed")
        if isinstance(schema.get("maxLength"), int) and len(value) > schema["maxLength"]:
            raise ValueError(f"{path} is longer than allowed")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            raise ValueError(f"{path} does not match the required pattern")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise ValueError(f"{path} is below the allowed minimum")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise ValueError(f"{path} is above the allowed maximum")


def _validate_schema_definition(schema: dict[str, Any], path: str = "$") -> None:
    unsupported = set(schema) - _SCHEMA_ANNOTATIONS - _SCHEMA_VALIDATORS
    if unsupported:
        keyword = sorted(unsupported)[0]
        raise ValueError(f"unsupported JSON Schema keyword '{keyword}' at {path}")
    expected = schema.get("type")
    types = [expected] if isinstance(expected, str) else expected
    if types is not None and (
        not isinstance(types, list)
        or not types
        or any(not isinstance(item, str) or item not in _SCHEMA_TYPES for item in types)
    ):
        raise ValueError(f"invalid JSON Schema type at {path}")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ValueError(f"JSON Schema properties must be an object at {path}")
    for name, child in properties.items():
        if not isinstance(name, str) or not isinstance(child, dict):
            raise ValueError(f"invalid JSON Schema property at {path}")
        _validate_schema_definition(child, f"{path}.{name}")
    required = schema.get("required", [])
    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        raise ValueError(f"JSON Schema required must be a list of strings at {path}")
    additional = schema.get("additionalProperties", True)
    if not isinstance(additional, (bool, dict)):
        raise ValueError(f"JSON Schema additionalProperties must be boolean or schema at {path}")
    if isinstance(additional, dict):
        _validate_schema_definition(additional, f"{path}.*")
    items = schema.get("items")
    if items is not None:
        if not isinstance(items, dict):
            raise ValueError(f"JSON Schema items must be a schema object at {path}")
        _validate_schema_definition(items, f"{path}[]")
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise ValueError(f"JSON Schema enum must be an array at {path}")
    for keyword in ("minimum", "maximum"):
        value = schema.get(keyword)
        if value is not None and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            raise ValueError(f"JSON Schema {keyword} must be numeric at {path}")
    for keyword in ("minLength", "maxLength"):
        value = schema.get(keyword)
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise ValueError(f"JSON Schema {keyword} must be a non-negative integer at {path}")
    pattern = schema.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise ValueError(f"JSON Schema pattern must be a string at {path}")
        try:
            re.compile(pattern)
        except re.error:
            raise ValueError(f"invalid JSON Schema pattern at {path}") from None


class ToolRegistry:
    """Registry of explicitly injected tools; it has no default operational tools.

    Local validation supports JSON Schema's primitive types, object properties,
    required keys, additionalProperties, items, enum, const, numeric bounds,
    string lengths, and patterns. Other validation keywords fail registration
    instead of being silently treated as validated.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
    ) -> ToolDefinition:
        """Register a tool, rejecting duplicate names and invalid definitions."""
        if not isinstance(name, str) or not _TOOL_NAME.fullmatch(name):
            raise ValueError("tool name must contain 1-64 letters, digits, underscores, or hyphens")
        if name in self._tools:
            raise ValueError(f"tool '{name}' is already registered")
        if not isinstance(description, str):
            raise ValueError("tool description must be a string")
        if not callable(handler):
            raise ValueError("tool handler must be callable")
        if not isinstance(input_schema, dict):
            raise ValueError("tool input schema must be a JSON object")
        try:
            schema_copy = json.loads(
                json.dumps(input_schema, ensure_ascii=False, allow_nan=False)
            )
        except (TypeError, ValueError):
            raise ValueError("tool input schema must contain JSON-compatible values") from None
        if schema_copy.get("type") not in (None, "object"):
            raise ValueError("tool input schema must describe an object")
        _validate_schema_definition(schema_copy)
        definition = ToolDefinition(name, description, schema_copy, handler)
        self._tools[name] = definition
        return definition

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            ToolDefinition(
                tool.name,
                tool.description,
                json.loads(json.dumps(tool.input_schema)),
                tool.handler,
            )
            for tool in self._tools.values()
        )

    def provider_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": json.loads(json.dumps(tool.input_schema)),
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: Any) -> ToolOutcome:
        """Validate untrusted model arguments before calling the registered handler."""
        if not isinstance(name, str) or name not in self._tools:
            return ToolOutcome(error=f"Tool '{name}' is not registered.")
        if not isinstance(arguments, dict):
            return ToolOutcome(error="Tool arguments must be a JSON object.")
        tool = self._tools[name]
        try:
            _validate_value(arguments, tool.input_schema)
        except (TypeError, ValueError, re.error) as exc:
            return ToolOutcome(error=f"Invalid arguments: {exc}")
        try:
            result = tool.handler(arguments)
            json.dumps(result, ensure_ascii=False, allow_nan=False)
        except Exception as exc:
            return ToolOutcome(error=f"Tool handler failed: {type(exc).__name__}: {exc}")
        return ToolOutcome(result=result)
