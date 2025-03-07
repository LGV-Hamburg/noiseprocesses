from pydantic import BaseModel, ConfigDict, Field


class InputRequiredTables(BaseModel):
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


class InputOptionalTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    dem_table: str | None = Field(
        default=None,
        description="Digital Elevation Model table"
    )
    ground_absorption_table: str | None = Field(
        default=None,
        description="Ground absorption coefficients table"
    )

class IntermediateTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    emission_table: str = Field(
        default="EMISSIONS", description="Table with calculated noise emissions"
    )
    propagation_table: str = Field(
        default="PROPAGATION", description="Table with calculated noise levels"
    )
