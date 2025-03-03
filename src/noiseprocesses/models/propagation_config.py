from pydantic import BaseModel, ConfigDict, Field


class RequiredTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    building_table: str = Field(
        default="BUILDINGS",
        description="Buildings table with geometry and height"
    )
    roads_table: str = Field(
        default="ROADS_TRAFFIC",
        description="Road network table with traffic data"
    )
    receivers_table: str = Field(
        default="RECEIVERS",
        description="Receiver points table"
    )


class OptionalTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    dem_table: str = Field(
        default="DEM", description="Digital Elevation Model table")
    ground_absorption_table: str = Field(
        default="GROUNDS", description="Ground absorption coefficients table"
    )
