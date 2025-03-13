from typing import Literal

from pydantic import BaseModel, Field, field_validator

from noiseprocesses.models.propagation_config import OutputTablesNames


class IsoSurfaceConfig(BaseModel):
    noise_level_table: Literal[
        OutputTablesNames.l_day,
        OutputTablesNames.l_den,
        OutputTablesNames.l_evening,
        OutputTablesNames.l_night,
    ] = OutputTablesNames.l_den
    iso_classes: list | None = Field(
        default=None,
        description=(
            "Separation of sound levels for isosurfaces. Default is:\n"
            "35.0,40.0,45.0,50.0,55.0,60.0,65.0,70.0,75.0,80.0,200.0"
        )
    )
    smooth_coefficient: float = Field(
        default=0.5,
        ge=0.0,
        le=100.0,
        description=(
            "This coefficient (Bezier curve coefficient) \n"
            "will smooth the generated isosurfaces. \n"
            "If equal to 0, it disables the smoothing step."
        ),
    )
    @field_validator('iso_classes', mode="before")
    def validate_iso_classes(cls, value):
        # Convert string to list of floats
        try:
            values = [float(x.strip()) for x in value.split(',') if x.strip()]
            # Remove duplicates and sort
            return values
        except ValueError:
            raise ValueError(
                'iso_classes must be a valid comma-separated list of numbers'
            )



class IsoSurfaceUserSettings(BaseModel):
    iso_classes: str | None = Field(
        default=None,
        description=(
            "Separation of sound levels for isosurfaces. Default is:\n"
            "35.0,40.0,45.0,50.0,55.0,60.0,65.0,70.0,75.0,80.0,200.0"
        )
    )
    smooth_coefficient: float = Field(
        default=0.5,
        ge=0.0,
        le=100.0,
        description=(
            "This coefficient (Bezier curve coefficient) \n"
            "will smooth the generated isosurfaces. \n"
            "If equal to 0, it disables the smoothing step."
        ),
    )
    @field_validator('iso_classes', mode="before")
    def validate_iso_classes(cls, value):
        # Convert string to list of floats
        try:
            values = [float(x.strip()) for x in value.split(',') if x.strip()]
            # Remove duplicates and sort
            unique_sorted = sorted(set(values))
            # Convert back to string
            return ','.join(str(x) for x in unique_sorted)
        except ValueError:
            raise ValueError(
                'iso_classes must be a valid comma-separated list of numbers'
            )