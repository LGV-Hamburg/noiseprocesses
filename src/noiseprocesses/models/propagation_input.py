from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RequiredTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    building_table: str = Field(
        ..., description="Buildings table with geometry and height"
    )
    roads_table: str = Field(..., description="Road network table with traffic data")
    receivers_table: str = Field(..., description="Receiver points table")


class OptionalTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    dem_table: Optional[str] = Field(None, description="Digital Elevation Model table")
    ground_absorption_table: Optional[str] = Field(
        None, description="Ground absorption coefficients table"
    )
    dem_table: Optional[str] = Field(None, description="Digital Elevation Model table")
    ground_absorption_table: Optional[str] = Field(
        None, description="Ground absorption coefficients table"
    )
