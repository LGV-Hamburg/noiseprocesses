from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from pathlib import Path

class RequiredTables(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    building_table: str = Field(..., description="Buildings table with geometry and height")
    roads_table: str = Field(..., description="Road network table with traffic data")
    receivers_table: str = Field(..., description="Receiver points table")

class OptionalTables(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    dem_table: Optional[str] = Field(None, description="Digital Elevation Model table")
    ground_absorption_table: Optional[str] = Field(None, description="Ground absorption coefficients table")

class AcousticParameters(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    wall_alpha: float = Field(0.1, ge=0.0, le=1.0, description="Wall absorption coefficient")
    max_source_distance: float = Field(150.0, gt=0, description="Maximum source-receiver distance in meters")
    max_reflection_distance: float = Field(50.0, gt=0, description="Maximum reflection distance in meters")
    reflection_order: int = Field(1, ge=0, description="Number of reflections to consider")
    humidity: float = Field(70.0, ge=0.0, le=100.0, description="Relative humidity percentage")
    temperature: float = Field(15.0, ge=-20.0, le=50.0, description="Air temperature in Celsius")

class PropagationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    vertical_diffraction: bool = Field(False, description="Enable vertical edge diffraction")
    horizontal_diffraction: bool = Field(False, description="Enable horizontal edge diffraction")
    favorable_day: str = Field("0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5", 
                             description="Day favorable propagation conditions")
    favorable_evening: Optional[str] = Field(None, description="Evening favorable propagation conditions")
    favorable_night: Optional[str] = Field(None, description="Night favorable propagation conditions")

class OutputControls(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    skip_lday: bool = Field(False, description="Skip day period calculation")
    skip_levening: bool = Field(False, description="Skip evening period calculation")
    skip_lnight: bool = Field(False, description="Skip night period calculation")
    skip_lden: bool = Field(False, description="Skip day-evening-night calculation")
    export_source_id: bool = Field(False, description="Export source identifiers")
    rays_output_path: Optional[Path] = Field(None, description="Ray propagation export path")

class PerformanceSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    thread_count: int = Field(0, ge=0, description="Number of computation threads (0 = auto)")

class NoiseCalculationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    required_tables: RequiredTables
    optional_tables: OptionalTables = OptionalTables()
    acoustic_params: AcousticParameters = AcousticParameters()
    propagation_settings: PropagationSettings = PropagationSettings()
    output_controls: OutputControls = OutputControls()
    performance: PerformanceSettings = PerformanceSettings()