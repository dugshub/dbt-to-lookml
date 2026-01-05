"""DataModel domain - physical table/source representation."""

from enum import Enum

from pydantic import BaseModel, computed_field


class ConnectionType(str, Enum):
    """Supported connection/warehouse types."""

    REDSHIFT = "redshift"
    STARBURST = "starburst"
    POSTGRES = "postgres"
    DUCKDB = "duckdb"


class DataModel(BaseModel):
    """
    Represents a physical table/source.

    Supports 2-part (schema.table) or 3-part (catalog.schema.table) naming.
    """

    name: str
    catalog: str | None = None  # database in Snowflake, catalog in Starburst
    schema_name: str  # 'schema' is reserved in Pydantic
    table: str
    connection: ConnectionType

    @computed_field
    @property
    def fully_qualified(self) -> str:
        """Return fully qualified table name."""
        parts = [p for p in [self.catalog, self.schema_name, self.table] if p]
        return ".".join(parts)

    model_config = {"frozen": False, "extra": "forbid"}
