from typing import Dict, Optional
from pydantic import BaseModel, Field, model_validator
from ..core.java_bridge import JavaBridge
from ..core.database import NoiseDatabase
from pathlib import Path

class TrafficFlow(BaseModel):
    """Traffic flow parameters for a road segment following CNOSSOS-EU."""
    
    light_vehicles: float = Field(
        default=0.0,
        description="Hourly average light vehicle count",
        ge=0.0
    )
    medium_vehicles: float = Field(
        default=0.0,
        description="Hourly average medium vehicle count",
        ge=0.0
    )
    heavy_vehicles: float = Field(
        default=0.0,
        description="Hourly average heavy vehicle count",
        ge=0.0
    )
    light_motorcycles: float = Field(
        default=0.0,
        description="Hourly average mopeds count",
        ge=0.0
    )
    heavy_motorcycles: float = Field(
        default=0.0,
        description="Hourly average motorcycles count",
        ge=0.0
    )
    
    light_speed: float = Field(
        default=50.0,
        description="Light vehicle speed (km/h)",
        ge=0.0,
        le=200.0
    )
    medium_speed: float = Field(
        default=50.0,
        description="Medium vehicle speed (km/h)",
        ge=0.0,
        le=200.0
    )
    heavy_speed: float = Field(
        default=50.0,
        description="Heavy vehicle speed (km/h)",
        ge=0.0,
        le=200.0
    )
    light_moto_speed: float = Field(
        default=50.0,
        description="Light motorcycle speed (km/h)",
        ge=0.0,
        le=200.0
    )
    heavy_moto_speed: float = Field(
        default=50.0,
        description="Heavy motorcycle speed (km/h)",
        ge=0.0,
        le=200.0
    )
    
    pavement: str = Field(
        default="NL08",
        description="Road surface type (CNOSSOS-EU)",
        pattern=r"^[A-Z]{2}\d{2}$"
    )
    temperature: float = Field(
        default=20.0,
        description="Temperature in °C",
        ge=-20.0,
        le=50.0
    )

    @model_validator(mode='after')
    def check_speeds(self) -> 'TrafficFlow':
        """Validate that speeds are reasonable for vehicle types."""
        if self.heavy_speed > self.light_speed:
            raise ValueError("Heavy vehicle speed cannot exceed light vehicle speed")
        if self.medium_speed > self.light_speed:
            raise ValueError("Medium vehicle speed cannot exceed light vehicle speed")
        return self
