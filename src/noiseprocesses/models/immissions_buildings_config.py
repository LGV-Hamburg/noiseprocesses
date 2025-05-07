import logging
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
)

from noiseprocesses.models.grid_config import BuildingGridSettingsUser
from noiseprocesses.models.propagation_config import (
    InputOptionalTables,
    InputRequiredTables,
)

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
    building_grid_settings: BuildingGridSettingsUser = (
        BuildingGridSettingsUser()
    )  # internal defaults, user overridable
    performance: PerformanceSettings = PerformanceSettings()