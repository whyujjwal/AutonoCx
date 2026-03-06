"""Tool parameter validation using JSON Schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of validating tool parameters against a schema."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    sanitised_params: dict = field(default_factory=dict)


class ParameterValidator:
    """Validate tool call parameters against a JSON Schema definition.

    Uses ``jsonschema`` when available; falls back to a lightweight
    built-in check that covers the most common cases (required fields,
    type checks, enum constraints).
    """

    def validate(
        self,
        parameters: dict[str, Any],
        schema: dict[str, Any],
    ) -> ValidationResult:
        """Validate *parameters* against *schema*.

        Returns a ``ValidationResult`` with ``is_valid=True`` when all
        constraints pass, or ``is_valid=False`` with descriptive errors.
        """
        errors: list[str] = []

        # Try jsonschema first
        try:
            import jsonschema  # type: ignore[import-untyped]

            try:
                jsonschema.validate(instance=parameters, schema=schema)
                return ValidationResult(
                    is_valid=True,
                    sanitised_params=dict(parameters),
                )
            except jsonschema.ValidationError as exc:
                errors.append(str(exc.message))
                return ValidationResult(is_valid=False, errors=errors)
            except jsonschema.SchemaError as exc:
                logger.warning("invalid_tool_schema", error=str(exc))
                errors.append(f"Invalid tool schema: {exc.message}")
                return ValidationResult(is_valid=False, errors=errors)
        except ImportError:
            pass

        # Fallback: lightweight built-in validation
        return self._builtin_validate(parameters, schema)

    # ------------------------------------------------------------------
    # Built-in validation (no external dependency)
    # ------------------------------------------------------------------

    def _builtin_validate(
        self,
        parameters: dict[str, Any],
        schema: dict[str, Any],
    ) -> ValidationResult:
        errors: list[str] = []
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        # Check required fields
        for field_name in required:
            if field_name not in parameters:
                errors.append(f"Missing required parameter: '{field_name}'")

        # Validate each provided parameter
        for key, value in parameters.items():
            if key not in properties:
                if schema.get("additionalProperties") is False:
                    errors.append(f"Unexpected parameter: '{key}'")
                continue

            prop_schema = properties[key]
            field_errors = self._validate_field(key, value, prop_schema)
            errors.extend(field_errors)

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        return ValidationResult(is_valid=True, sanitised_params=dict(parameters))

    @staticmethod
    def _validate_field(name: str, value: Any, schema: dict) -> list[str]:
        """Validate a single field against its schema definition."""
        errors: list[str] = []
        expected_type = schema.get("type")

        # Type checking
        type_map: dict[str, tuple[type, ...]] = {
            "string": (str,),
            "integer": (int,),
            "number": (int, float),
            "boolean": (bool,),
            "array": (list,),
            "object": (dict,),
        }

        if expected_type and expected_type in type_map:
            if not isinstance(value, type_map[expected_type]):
                errors.append(
                    f"Parameter '{name}' must be {expected_type}, got {type(value).__name__}"
                )
                return errors  # Skip further checks if type is wrong

        # String constraints
        if expected_type == "string" and isinstance(value, str):
            min_len = schema.get("minLength")
            max_len = schema.get("maxLength")
            if min_len is not None and len(value) < min_len:
                errors.append(f"Parameter '{name}' must be at least {min_len} characters")
            if max_len is not None and len(value) > max_len:
                errors.append(f"Parameter '{name}' must be at most {max_len} characters")

        # Numeric constraints
        if expected_type in ("integer", "number") and isinstance(value, (int, float)):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and value < minimum:
                errors.append(f"Parameter '{name}' must be >= {minimum}")
            if maximum is not None and value > maximum:
                errors.append(f"Parameter '{name}' must be <= {maximum}")

        # Enum constraint
        enum_values = schema.get("enum")
        if enum_values is not None and value not in enum_values:
            errors.append(f"Parameter '{name}' must be one of {enum_values}")

        return errors
