"""Shared utilities for the ai package."""

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(filename: str, path: Path | str | None = None) -> str:
    """Load a prompt template from a file.

    Args:
        filename: Default file name inside ai/prompts/
        path: Override path to a custom prompt file (optional)

    Returns:
        The prompt template string
    """
    resolved = Path(path) if path else _PROMPTS_DIR / filename
    return resolved.read_text(encoding="utf-8").strip()


def pg_type_to_iso19110(pg_type: str) -> str:
    """Map a PostgreSQL column type string to its ISO 19110 equivalent.

    Args:
        pg_type: Raw PostgreSQL type string as returned by SQLAlchemy (e.g. "VARCHAR(50)").

    Returns:
        ISO 19110 type string (e.g. "string (50)").
    """
    t = pg_type.strip().upper()

    # VARCHAR(n) / CHARACTER VARYING(n)
    m = re.match(r"(?:VARCHAR|CHARACTER VARYING)\((\d+)\)", t)
    if m:
        return f"string ({m.group(1)})"

    # CHAR(n)
    m = re.match(r"(?:CHAR|CHARACTER)\((\d+)\)", t)
    if m:
        return f"string ({m.group(1)})"

    # NUMERIC(p, s) / DECIMAL(p, s)
    m = re.match(r"(?:NUMERIC|DECIMAL)\((\d+),\s*(\d+)\)", t)
    if m:
        return f"decimal ({m.group(1)}, {m.group(2)})"

    # NUMERIC(p) / DECIMAL(p)
    m = re.match(r"(?:NUMERIC|DECIMAL)\((\d+)\)", t)
    if m:
        return f"number ({m.group(1)})"

    mappings: dict[str, str] = {
        "TEXT": "string",
        "VARCHAR": "string",
        "INTEGER": "integer",
        "INT": "integer",
        "INT4": "integer",
        "INT8": "integer",
        "BIGINT": "integer",
        "SMALLINT": "integer",
        "INT2": "integer",
        "NUMERIC": "number",
        "DECIMAL": "number",
        "REAL": "real",
        "FLOAT4": "real",
        "FLOAT": "real",
        "DOUBLE PRECISION": "real",
        "FLOAT8": "real",
        "SERIAL": "integer",
        "BIGSERIAL": "integer",
        "BOOLEAN": "boolean",
        "BOOL": "boolean",
        "DATE": "date",
        "TIMESTAMP": "datetime",
        "TIMESTAMP WITHOUT TIME ZONE": "datetime",
        "TIMESTAMP WITH TIME ZONE": "datetime",
        "TIMESTAMPTZ": "datetime",
        "TIME": "time",
        "UUID": "string (36)",
        "JSON": "string",
        "JSONB": "string",
        "GEOMETRY": "GM_Object",
    }

    # Geometry subtypes (e.g. "GEOMETRY(POINT, 4326)")
    if t.startswith("GEOMETRY"):
        m = re.match(r"GEOMETRY\((\w+)", t)
        if m:
            geom_type = m.group(1).capitalize()
            return f"GM_{geom_type}"
        return "GM_Object"

    return mappings.get(t, pg_type.lower())
