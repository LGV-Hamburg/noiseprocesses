from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from noiseprocesses.models.propagation_config import (
    InputOptionalTables,
    InputRequiredTables,
)


class AcousticParameters(BaseModel):
    model_config = ConfigDict(frozen=True)

    wall_alpha: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Wall absorption coefficient"
    )
    max_source_distance: float = Field(
        default=150.0, gt=0, description="Maximum source-receiver distance in meters"
    )
    max_reflection_distance: float = Field(
        default=50.0, gt=0, description="Maximum reflection distance in meters"
    )
    reflection_order: int = Field(
        default=1, ge=0, description="Number of reflections to consider"
    )
    humidity: float = Field(
        default=70.0, ge=0.0, le=100.0, description="Relative humidity percentage"
    )
    temperature: float = Field(
        default=15.0, ge=-20.0, le=50.0, description="Air temperature in Celsius"
    )


class PropagationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    vertical_diffraction: bool = Field(
        default=False, description="Enable vertical edge diffraction"
    )
    horizontal_diffraction: bool = Field(
        default=False, description="Enable horizontal edge diffraction"
    )
    favorable_day: str = Field(
        default="0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5",
        description="Day favorable propagation conditions",
    )
    favorable_evening: Optional[str] = Field(
        default=None, description="Evening favorable propagation conditions"
    )
    favorable_night: Optional[str] = Field(
        default=None, description="Night favorable propagation conditions"
    )


class OutputControls(BaseModel):
    model_config = ConfigDict(frozen=True)

    skip_lday: bool = Field(default=False, description="Skip day period calculation")
    skip_levening: bool = Field(
        default=False, description="Skip evening period calculation"
    )
    skip_lnight: bool = Field(
        default=False, description="Skip night period calculation"
    )
    skip_lden: bool = Field(
        default=False, description="Skip day-evening-night calculation"
    )
    export_source_id: bool = Field(
        default=False, description="Export source identifiers"
    )
    rays_output_path: Optional[Path] = Field(
        default=None, description="Ray propagation export path"
    )


class PerformanceSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    thread_count: int = Field(
        default=0, ge=0, description="Number of computation threads (0 = auto)"
    )

class DatabaseConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "Noise"
    in_memory: bool = False

class NoiseCalculationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    database: DatabaseConfig = DatabaseConfig()
    required_tables: InputRequiredTables = InputRequiredTables()
    optional_tables: InputOptionalTables = InputOptionalTables()
    acoustic_params: AcousticParameters = AcousticParameters()
    propagation_settings: PropagationSettings = PropagationSettings()
    output_controls: OutputControls = OutputControls()
    performance: PerformanceSettings = PerformanceSettings()
