from dataclasses import dataclass


class ToolValidationError(ValueError):
    pass


@dataclass(frozen=True)
class FieldSpec:
    name: str
    field_type: type
    required: bool = True


@dataclass(frozen=True)
class ToolSpec:
    input_fields: list = None
    output_fields: list = None

    def validate_input(self, payload: dict):
        _validate_mapping("input", payload, self.input_fields or [])

    def validate_output(self, payload):
        if self.output_fields:
            _validate_mapping("output", payload, self.output_fields)


def _validate_mapping(stage: str, payload, fields):
    if not isinstance(payload, dict):
        raise ToolValidationError(f"{stage} payload must be a dict")

    for field in fields:
        if field.required and field.name not in payload:
            raise ToolValidationError(f"missing {stage} field: {field.name}")
        if field.name in payload and not isinstance(payload[field.name], field.field_type):
            expected = field.field_type.__name__
            actual = type(payload[field.name]).__name__
            raise ToolValidationError(
                f"{stage} field {field.name} expected {expected}, got {actual}"
            )
