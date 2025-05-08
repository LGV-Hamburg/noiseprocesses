import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Optional

from geojson_pydantic import FeatureCollection
from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from noiseprocesses.models.building_properties import BuildingsFeatureCollection
from noiseprocesses.models.dem_feature import BboxFeature
from noiseprocesses.models.grid_config import BuildingGridSettingsUser, GridSettingsUser
from noiseprocesses.models.ground_absorption import GroundAbsorptionFeatureCollection
from noiseprocesses.models.isosurface_config import IsoSurfaceUserSettings
from noiseprocesses.models.propagation_config import (
    InputOptionalTables,
    InputRequiredTables,
)
from noiseprocesses.models.roads_properties import RoadsFeature, RoadsFeatureCollection

logger = logging.getLogger(__name__)


class AcousticParameters(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    model_config = ConfigDict(extra="ignore")

    vertical_diffraction: bool = Field(
        default=False, description="Enable vertical edge diffraction"
    )
    horizontal_diffraction: bool = Field(
        default=True, description="Enable horizontal edge diffraction"
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


class OutputDayTimeSoundLevels(StrEnum):
    noise_day = "noise_day"
    noise_evening = "noise_evening"
    noise_night = "noise_night"
    noise_den = "noise_den"


class AdditionalDataOutputControls(BaseModel):
    export_source_id: bool = Field(
        default=False,
        description=(
            "Keep source identifier in output in order to get "
            "noise contribution of each noise source."
        ),
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
    model_config = ConfigDict(extra="ignore")

    database: DatabaseConfig = DatabaseConfig()
    required_input: InputRequiredTables = InputRequiredTables()
    optional_input: InputOptionalTables = InputOptionalTables()
    acoustic_params: AcousticParameters = (
        AcousticParameters()
    )  # internal defaults, user overridable
    propagation_settings: PropagationSettings = (
        PropagationSettings()
    )  # internal defaults, user overridable
    output_controls: dict[OutputDayTimeSoundLevels, dict] = {
        OutputDayTimeSoundLevels.noise_den: {}
    }  # internal defaults, user overridable
    additional_output_controls: AdditionalDataOutputControls = (
        AdditionalDataOutputControls()
    )
    receiver_grid_settings: GridSettingsUser = (
        GridSettingsUser()
    )  # internal defaults, user overridable
    building_grid_settings: BuildingGridSettingsUser | None = (
        None  # internal defaults, user overridable
    )
    performance: PerformanceSettings = PerformanceSettings()


Crs = Annotated[
    str | int,
    Field(
        description=(
            "Coordinate reference system (CRS) of the input data in "
            "the form of: 'http://www.opengis.net/def/crs/EPSG/0/25832', "
            "or as EPSG integer code."
        )
    ),
]


class NoiseCalculationUserInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    buildings: BuildingsFeatureCollection
    roads: RoadsFeatureCollection
    crs: Crs
    dem_url: AnyUrl | None = None
    dem_bbox_feature: BboxFeature | None = None
    ground_absorption: GroundAbsorptionFeatureCollection | None = None
    acoustic_parameters: AcousticParameters | None = None
    propagation_settings: PropagationSettings | None = None
    receiver_grid_settings: GridSettingsUser | None = None
    building_grid_settings: BuildingGridSettingsUser | None = None
    isosurface_settings: IsoSurfaceUserSettings | None = None

    @model_validator(mode="before")
    def validate_and_filter_roads(cls, values):
        roads = values.get("roads")
        if roads:
            valid_features = []
            for i, feature in enumerate(roads["features"]):
                try:
                    # Validate the properties field of each feature
                    RoadsFeature(**feature)
                    valid_features.append(feature)
                except ValidationError as e:
                    # Log the invalid feature and continue
                    logger.warning(f"Invalid feature in 'roads' at index {i}: {e}")
            # Replace the roads FeatureCollection with only valid features
            values["roads"] = FeatureCollection(
                features=valid_features, type="FeatureCollection"
            )
            logger.info(
                "Importing %d valid road features from %d road features.",
                len(valid_features),
                len(roads["features"]),
            )
        return values

    @model_validator(mode="before")
    def validate_feature_collections(cls, values):
        # Validate roads
        roads = values.get("roads")
        if roads and not roads["features"]:
            raise ValueError("The 'roads' FeatureCollection contains no features.")

        # Validate buildings
        buildings = values.get("buildings")
        if buildings and not buildings["features"]:
            raise ValueError("The 'buildings' FeatureCollection contains no features.")

        # Validate ground absorption
        ground_absorption = values.get("ground_absorption")
        if ground_absorption and not ground_absorption["features"]:
            raise ValueError(
                "The 'ground_absorption' FeatureCollection contains no features."
            )

        return values


if __name__ == "__main__":
    import json

    schema = NoiseCalculationUserInput.model_json_schema()

    with open("schema.json", "w") as file:
        json.dump(schema, file, indent=4)
