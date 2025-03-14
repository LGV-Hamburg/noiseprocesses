from enum import Enum

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


class LoudnessOutputTables(BaseModel):
    model_config = ConfigDict(frozen=True)

    loudness_day_result_table: str = Field(
        default="LDAY_RESULT",
        description="Table with calculated loudness day levels",
    )
    loudness_evening_result_table: str = Field(
        default="LEVENING_RESULT",
        description="Table with calculated loudness evening levels"
    )
    loudness_night_result_table: str = Field(
        default="LNIGHT_RESULT",
        description="Table with calculated loudness night levels"
    )
    loudness_den_result_table: str = Field(
        default="LDEN_RESULT",
        description="Table with calculated loudness den levels"
    )
    loudness_day_geometry_table: str = Field(
        default="LDAY_GEOM",
        description="Table with calculated loudness day geometry"
    )
    loudness_evening_geometry_table: str = Field(
        default="LEVENING_GEOM",
        description="Table with calculated loudness evening geometry"
    )
    loudness_night_geometry_table: str = Field(
        default="LNIGHT_GEOM",
        description="Table with calculated loudness night geometry"
    )
    loudness_den_geometry_table: str = Field(
        default="LDEN_GEOM",
        description="Table with calculated loudness den geometry"
    )
