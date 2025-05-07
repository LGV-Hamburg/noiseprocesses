import logging
from enum import Enum, StrEnum
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
from noiseprocesses.models.grid_config import BuildingGridConfig, BuildingGridConfig2d, GridSettingsUser
from noiseprocesses.models.ground_absorption import GroundAbsorptionFeatureCollection
from noiseprocesses.models.isosurface_config import IsoSurfaceUserSettings
from noiseprocesses.models.propagation_config import (
    InputOptionalTables,
    InputRequiredTables,
)
from noiseprocesses.models.roads_properties import RoadsFeature, RoadsFeatureCollection
from noiseprocesses.models.noise_calculation_config import (
    AcousticParameters, PropagationSettings,
    PerformanceSettings, DatabaseConfig

)
logger = logging.getLogger(__name__)

class OutputReceiversTables(StrEnum):
    """Output receiver types"""

    noise_den = "LDEN_GEOM"
    noise_day = "LDAY_GEOM"
    noise_evening = "LEVENING_GEOM"
    noise_night = "LNIGHT_GEOM"


class ImmissionBuildingsCalculationConfig(BaseModel):
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
    output_controls: dict[OutputReceiversTables, dict] = {
        OutputReceiversTables.noise_den: {}
    }  # internal defaults, user overridable
    building_grid_settings: BuildingGridConfig = (
        BuildingGridConfig2d()
    )  # internal defaults, user overridable
    performance: PerformanceSettings = PerformanceSettings()