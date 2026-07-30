"""Tool protocol, strict argument validation, and registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


SUPPORTED_JSON_TYPES = {
    "array": list,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
    "object": dict,
    "string": str,
}


class ToolParameterError(ValueError):
    """Raised when tool arguments violate the declared schema."""


@dataclass(frozen=True)
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Tool name must be a non-empty string")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Tool description must be a non-empty string")
        if not isinstance(self.parameters, dict):
            raise TypeError("Tool parameters must be a dict")
        if self.parameters.get("type") != "object":
            raise ValueError("Tool parameters schema must be an object schema")
        properties = self.parameters.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("Tool parameters schema must define properties")
        required = self.parameters.get("required", [])
        if not isinstance(required, list):
            raise TypeError("Tool required fields must be a list")
        for field_name in required:
            if field_name not in properties:
                raise ValueError(f"Required field is missing from properties: {field_name}")

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_args(self, args: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(args, dict):
            raise ToolParameterError("Tool arguments must be a dict")

        properties = self.parameters["properties"]
        required = set(self.parameters.get("required", []))
        additional_allowed = self.parameters.get("additionalProperties", False)

        missing = sorted(field for field in required if field not in args)
        if missing:
            raise ToolParameterError("Missing required tool arguments: " + ", ".join(missing))

        if additional_allowed is not True:
            unknown = sorted(field for field in args if field not in properties)
            if unknown:
                raise ToolParameterError("Unknown tool arguments: " + ", ".join(unknown))

        for field_name, value in args.items():
            field_schema = properties.get(field_name)
            if field_schema is None:
                continue
            self._validate_value(field_name, value, field_schema)

        return dict(args)

    def _validate_value(
        self,
        field_name: str,
        value: Any,
        field_schema: dict[str, Any],
    ) -> None:
        expected_type = field_schema.get("type")
        if expected_type not in SUPPORTED_JSON_TYPES:
            raise ToolParameterError(f"Unsupported schema type for {field_name}: {expected_type}")

        if expected_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ToolParameterError(f"Tool argument {field_name} must be a number")
        elif expected_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ToolParameterError(f"Tool argument {field_name} must be an integer")
        elif not isinstance(value, SUPPORTED_JSON_TYPES[expected_type]):
            raise ToolParameterError(f"Tool argument {field_name} must be {expected_type}")

        enum_values = field_schema.get("enum")
        if enum_values is not None and value not in enum_values:
            raise ToolParameterError(
                f"Tool argument {field_name} must be one of: {', '.join(map(str, enum_values))}"
            )


class Tool(Protocol):
    @property
    def schema(self) -> ToolSchema:
        """Return the tool schema."""

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with already validated arguments."""


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        schema = tool.schema
        if not isinstance(schema, ToolSchema):
            raise TypeError("Tool schema must be a ToolSchema")
        if schema.name in self._tools:
            raise ValueError(f"Tool already registered: {schema.name}")
        self._tools[schema.name] = tool

    def get(self, name: str) -> Tool:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool name must be a non-empty string")
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool is not registered: {name}") from exc

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self.get(name)
        validated_args = tool.schema.validate_args(args)
        result = tool.run(validated_args)
        if not isinstance(result, dict):
            raise TypeError("Tool result must be a dict")
        return result

    def tool_schemas(self) -> list[ToolSchema]:
        return [tool.schema for tool in self._tools.values()]

    def openai_tools(self) -> list[dict[str, Any]]:
        return [schema.to_openai_tool() for schema in self.tool_schemas()]
