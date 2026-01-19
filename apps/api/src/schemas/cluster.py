from src.schemas.base import SchemaBaseModel


class ClusterResponse(SchemaBaseModel):
    level: int
    id: str
    label: str
    description: str
    value: int
    parent: str | None = None
    density: float | None = None
    density_rank: int | None = None
    density_rank_percentile: float | None = None


class ClusterUpdate(SchemaBaseModel):
    id: str
    label: str
    description: str
