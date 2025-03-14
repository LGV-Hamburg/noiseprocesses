from pathlib import Path
from typing import Optional

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

from noiseprocesses.models.propagation_config import (
    InputOptionalTables,
    InputRequiredTables,
)

from geojson_pydantic import Feature, LineString, MultiLineString, Polygon
from geojson_pydantic.features import FeatureCollection
from noiseprocesses.models.grid_config import GridSettingsUser
from noiseprocesses.models.isosurface_config import IsoSurfaceUserSettings
from noiseprocesses.models.roads_properties import TrafficFlow
from noiseprocesses.models.building_properties import BuildingProperties
from noiseprocesses.models.ground_absorption import GroundAbsorption

BuildingsFeatureCollection = FeatureCollection[
    Feature[Polygon, BuildingProperties]
]
RoadsFeatureCollection = FeatureCollection[
    Feature[LineString | MultiLineString, TrafficFlow]
]
GroundAbsorptionFeatureCollection = FeatureCollection[
    Feature[Polygon, GroundAbsorption]
]



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


class NoiseLevelsOutputControls(BaseModel):
    model_config = ConfigDict(frozen=True)

    skip_lday: bool = Field(
        default=False, description="Skip day period noise calculation"
    )
    skip_levening: bool = Field(
        default=False, description="Skip evening period noise calculation"
    )
    skip_lnight: bool = Field(
        default=False, description="Skip night period noise calculation"
    )
    skip_lden: bool = Field(
        default=False, description="Skip day-evening-night noise calculation"
    )

class AdditionalDataOutputControls(BaseModel):
    export_source_id: bool = Field(
        default=False, description=(
            "Keep source identifier in output in order to get "
            "noise contribution of each noise source."
        )
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
    required_input: InputRequiredTables = InputRequiredTables()
    optional_input: InputOptionalTables = InputOptionalTables()
    acoustic_params: AcousticParameters = AcousticParameters() # internal defaults, user overridable
    propagation_settings: PropagationSettings = PropagationSettings() # internal defaults, user overridable
    output_controls: NoiseLevelsOutputControls = NoiseLevelsOutputControls() # internal defaults, user overridable
    additional_output_controls: AdditionalDataOutputControls = AdditionalDataOutputControls()
    performance: PerformanceSettings = PerformanceSettings()

class NoiseCalculationUserInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    buildings: BuildingsFeatureCollection
    roads: RoadsFeatureCollection
    dem: AnyUrl | None = None
    ground_absorption: GroundAbsorptionFeatureCollection | None = None
    acoustic_parameters: AcousticParameters | None = None
    propagation_settings: PropagationSettings | None = None
    receiver_grid_settings: GridSettingsUser | None = None
    iosurface_settings: IsoSurfaceUserSettings | None = None
    noise_output_controls: NoiseLevelsOutputControls | None = None


if __name__ == "__main__":

    import json
    schema = NoiseCalculationUserInput.model_json_schema()

    with open("schema.json", "w") as file:
        json.dump(schema, file, indent=4)
    