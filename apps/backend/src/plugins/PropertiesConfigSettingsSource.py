import os
from pathlib import Path
from string import Template
from typing import Any

from pydantic import AliasChoices
from pydantic.aliases import AliasPath
from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from src.core.paths import get_default_datadir


class PropertiesConfigSettingsSource(PydanticBaseSettingsSource):
    def _load_properties(self) -> dict[str, str]:
        datadirpath: str = get_default_datadir()
        encoding = self.config.get("env_file_encoding", "utf-8")
        path = Path(f"{datadirpath}/default.properties")

        data: dict[str, str] = {}
        if not path.exists():
            return data
        for line in path.read_text(encoding).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()

        return data

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        properties = self._load_properties()
        field_value = properties.get(field_name)

        # Check validation_alias (handles both string and AliasChoices)
        if field_value is None and field.validation_alias:
            if isinstance(field.validation_alias, AliasChoices):
                for alias in field.validation_alias.choices:
                    alias_str = str(alias) if isinstance(alias, AliasPath) else alias
                    field_value = properties.get(alias_str)
                    if field_value is not None:
                        field_name = alias_str
                        break
            else:
                alias_str = (
                    str(field.validation_alias)
                    if isinstance(field.validation_alias, AliasPath)
                    else field.validation_alias
                )
                field_value = properties.get(alias_str)

        # Fallback to alias
        if field_value is None and field.alias:
            alias_str = str(field.alias) if isinstance(field.alias, AliasPath) else field.alias
            field_value = properties.get(alias_str)

        return field_value, field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        # Let Pydantic handle type coercion (bool, int, etc.)
        return value

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_name, _ = self.get_field_value(field, field_name)
            if field_value is not None:
                key = field.alias or field_name  # use alias if defined
                try:
                    d[key] = Template(field_value).substitute(os.environ)
                except KeyError:
                    print(
                        "Couldn't substitute env vars for",
                        field_name,
                        "set in default.properties, surely missing? Fallback to other sources.",
                    )

        return d
