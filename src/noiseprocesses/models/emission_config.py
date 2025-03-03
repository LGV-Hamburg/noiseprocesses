from pydantic import BaseModel, Field, ConfigDict
from typing import List
from enum import Enum

class FrequencyBands(Enum):
    """Standard frequency bands used in acoustic calculations"""
    OCTAVE = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    THIRD_OCTAVE = [50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 
                    800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 
                    8000, 10000]

class TimePeriod(str, Enum):
    """Standard acoustic time periods"""
    DAY = "D"
    EVENING = "E"
    NIGHT = "N"

class NoiseModellingConfig(BaseModel):
    """Base configuration for NoiseModelling calculations"""
    model_config = ConfigDict(frozen=True)

    coefficient_version: int = Field(
        default=2,
        description=(
            "Updated CNOSSOS-EU (2021) with corrections for: "
            "Rolling noise coefficients, "
            "Vehicle categories, "
            "Road surface corrections, "
            "Railway source modeling"
        )
    )

class RoadEmissionConfig(NoiseModellingConfig):
    """Configuration for road noise emission calculations"""
    model_config = ConfigDict(frozen=True)
    
    road_table: str = Field(
        default="ROADS_TRAFFIC",
        description="Road network table name with traffic data"
    )
    frequency_bands: List[int] = Field(
        default=FrequencyBands.OCTAVE.value,
        description="Octave bands used for road noise calculation"
    )
    time_periods: List[TimePeriod] = Field(
        default=[TimePeriod.DAY, TimePeriod.EVENING, TimePeriod.NIGHT],
        description="Time periods to calculate"
    )