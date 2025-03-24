from enum import IntEnum
from typing import Optional, Self
from geojson_pydantic import Feature, FeatureCollection, LineString, MultiLineString
from pydantic import BaseModel, Field, model_validator

# PK </b>* : an identifier. It shall be a primary key (INTEGER, PRIMARY KEY)</li>' +
# LV_D </b><b>TV_E </b><b> TV_N </b> : Hourly average light vehicle count (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# MV_D </b><b>MV_E </b><b>MV_N </b> : Hourly average medium heavy vehicles, delivery vans > 3.5 tons,  buses, touring cars, etc. with two axles and twin tyre mounting on rear axle count (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# HGV_D </b><b> HGV_E </b><b> HGV_N </b> :  Hourly average heavy duty vehicles, touring cars, buses, with three or more axles (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# WAV_D </b><b> WAV_E </b><b> WAV_N </b> :  Hourly average mopeds, tricycles or quads &le; 50 cc count (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# WBV_D </b><b> WBV_E </b><b> WBV_N </b> :  Hourly average motorcycles, tricycles or quads > 50 cc count (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# LV_SPD_D </b><b> LV_SPD_E </b><b>LV_SPD_N </b> :  Hourly average light vehicle speed (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# MV_SPD_D </b><b> MV_SPD_E </b><b>MV_SPD_N </b> :  Hourly average medium heavy vehicles speed (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# HGV_SPD_D </b><b> HGV_SPD_E </b><b> HGV_SPD_N </b> :  Hourly average heavy duty vehicles speed (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# WAV_SPD_D </b><b> WAV_SPD_E </b><b> WAV_SPD_N </b> :  Hourly average mopeds, tricycles or quads &le; 50 cc speed (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# WBV_SPD_D </b><b> WBV_SPD_E </b><b> WBV_SPD_N </b> :  Hourly average motorcycles, tricycles or quads > 50 cc speed (6-18h)(18-22h)(22-6h) (DOUBLE)</li>' +
# PVMT </b> :  CNOSSOS road pavement identifier (ex: NL05)(default NL08) (VARCHAR)</li>' +
# TEMP_D </b><b> TEMP_E </b><b> TEMP_N </b> : Average day, evening, night temperature (default 20&#x2103;) (6-18h)(18-22h)(22-6h)(DOUBLE)</li>' +
# TS_STUD </b> : A limited period Ts (in months) over the year where a average proportion pm of light vehicles are equipped with studded tyres (0-12) (DOUBLE)</li>' +
# PM_STUD </b> : Average proportion of vehicles equipped with studded tyres during TS_STUD period (0-1) (DOUBLE)</li>' +
# JUNC_DIST </b> : Distance to junction in meters (DOUBLE)</li>' +
# JUNC_TYPE </b> : Type of junction (k=0 none, k = 1 for a crossing with traffic lights ; k = 2 for a roundabout) (INTEGER)</li>' +
# SLOPE </b> : Slope (in %) of the road section. If the field is not filled in, the LINESTRING z-values will be used to calculate the slope and the traffic direction (way field) will be force to 3 (bidirectional). (DOUBLE)</li>' +
# WAY </b> : Define the way of 

class JunctionType(IntEnum):
    """CNOSSOS junction types"""
    NONE = 0
    TRAFFIC_LIGHT = 1
    ROUNDABOUT = 2

class CnossosTrafficFlow(BaseModel):
    """Internal traffic flow parameters matching NoiseModelling field names."""
    
    @classmethod
    def from_user_model(cls, user_model: 'TrafficFlow') -> Self:
        """Convert from user model to internal model."""
        # Pydantic v2 model_dump() with by_alias=True converts to internal field names
        return cls(**user_model.model_dump(by_alias=True))
    PK: int = Field(
        alias="id",
        description="Unique identifier for the road segment",
    )
    # Vehicle counts - default None to match database behavior
    LV_D: float | None = Field(
        default=None,
        description="Light vehicles per hour (6-18h)",
        ge=0.0,
        alias="light_vehicles_day"
    )
    LV_E: float | None = Field(
        default=None,
        description="Light vehicles per hour (18-22h)",
        ge=0.0,
        alias="light_vehicles_evening"
    )
    LV_N: float | None = Field(
        default=None,
        description="Light vehicles per hour (22-6h)",
        ge=0.0,
        alias="light_vehicles_night"
    )
    
    MV_D: float | None = Field(
        default=None,
        description="Medium heavy vehicles per hour (6-18h)",
        ge=0.0,
        alias="medium_vehicles_day"
    )
    MV_E: float | None = Field(
        default=None,
        description="Medium heavy vehicles per hour (18-22h)",
        ge=0.0,
        alias="medium_vehicles_evening"
    )
    MV_N: float | None = Field(
        default=None,
        description="Medium heavy vehicles per hour (22-6h)",
        ge=0.0,
        alias="medium_vehicles_night"
    )
    
    HGV_D: float | None = Field(
        default=None,
        description="Heavy duty vehicles per hour (6-18h)",
        ge=0.0,
        alias="heavy_vehicles_day"
    )
    HGV_E: float | None = Field(
        default=None,
        description="Heavy duty vehicles per hour (18-22h)",
        ge=0.0,
        alias="heavy_vehicles_evening"
    )
    HGV_N: float | None = Field(
        default=None,
        description="Heavy duty vehicles per hour (22-6h)",
        ge=0.0,
        alias="heavy_vehicles_night"
    )
    
    WAV_D: float | None = Field(
        default=None,
        description="Mopeds ≤ 50cc per hour (6-18h)",
        ge=0.0,
        alias="light_motorcycles_day"
    )
    WAV_E: float | None = Field(
        default=None,
        description="Mopeds ≤ 50cc per hour (18-22h)",
        ge=0.0,
        alias="light_motorcycles_evening"
    )
    WAV_N: float | None = Field(
        default=None,
        description="Mopeds ≤ 50cc per hour (22-6h)",
        ge=0.0,
        alias="light_motorcycles_night"
    )
    
    WBV_D: float | None = Field(
        default=None,
        description="Motorcycles > 50cc per hour (6-18h)",
        ge=0.0,
        alias="heavy_motorcycles_day"
    )
    WBV_E: float | None = Field(
        default=None,
        description="Motorcycles > 50cc per hour (18-22h)",
        ge=0.0,
        alias="heavy_motorcycles_evening"
    )
    WBV_N: float | None = Field(
        default=None,
        description="Motorcycles > 50cc per hour (22-6h)",
        ge=0.0,
        alias="heavy_motorcycles_night"
    )
    
    # Speeds - required when corresponding count exists
    LV_SPD_D: float | None = Field(
        default=None,
        description="Light vehicle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
        alias="light_speed_day"
    )
    LV_SPD_E: float | None = Field(
        default=None,
        description="Light vehicle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
        alias="light_speed_evening"
    )
    LV_SPD_N: float | None = Field(
        default=None,
        description="Light vehicle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
        alias="light_speed_night"
    )
    
    MV_SPD_D: float | None = Field(
        default=None,
        description="Medium vehicle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
        alias="medium_speed_day"
    )
    MV_SPD_E: float | None = Field(
        default=None,
        description="Medium vehicle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
        alias="medium_speed_evening"
    )
    MV_SPD_N: float | None = Field(
        default=None,
        description="Medium vehicle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
        alias="medium_speed_night"
    )
    
    HGV_SPD_D: float | None = Field(
        default=None,
        description="Heavy vehicle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
        alias="heavy_speed_day"
    )
    HGV_SPD_E: float | None = Field(
        default=None,
        description="Heavy vehicle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
        alias="heavy_speed_evening"
    )
    HGV_SPD_N: float | None = Field(
        default=None,
        description="Heavy vehicle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
        alias="heavy_speed_night"
    )
    
    WAV_SPD_D: float | None = Field(
        default=None,
        description="Moped speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
        alias="light_moto_speed_day"
    )
    WAV_SPD_E: float | None = Field(
        default=None,
        description="Moped speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
        alias="light_moto_speed_evening"
    )
    WAV_SPD_N: float | None = Field(
        default=None,
        description="Moped speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
        alias="light_moto_speed_night"
    )
    
    WBV_SPD_D: float | None = Field(
        default=None,
        description="Motorcycle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
        alias="heavy_moto_speed_day"
    )
    WBV_SPD_E: float | None = Field(
        default=None,
        description="Motorcycle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
        alias="heavy_moto_speed_evening"
    )
    WBV_SPD_N: float | None = Field(
        default=None,
        description="Motorcycle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
        alias="heavy_moto_speed_night"
    )
    
    # Road properties with defaults from CNOSSOS
    PVMT: str = Field(
        default="NL08",
        description="CNOSSOS road surface type",
        pattern=r"^(NL(0[1-9]|1[0-4])|DEF)$",
        alias="pavement"
    )
    
    TEMP_D: float = Field(
        default=20.0,
        description="Temperature in °C (6-18h)",
        alias="temperature_day"
    )
    TEMP_E: float = Field(
        default=20.0,
        description="Temperature in °C (18-22h)",
        alias="temperature_evening"
    )
    TEMP_N: float = Field(
        default=20.0,
        description="Temperature in °C (22-6h)",
        alias="temperature_night"
    )
    
    TS_STUD: float | None = Field(
        default=None,
        description="Months with studded tires (0-12)",
        ge=0.0,
        le=12.0,
        alias="studded_tires_months"
    )
    PM_STUD: float | None = Field(
        default=None,
        description="Ratio of vehicles with studded tires (0-1)",
        ge=0.0,
        le=1.0,
        alias="studded_tires_ratio"
    )
    
    JUNC_DIST: float | None = Field(
        default=None,
        description="Distance to junction in meters",
        ge=0.0,
        alias="junction_distance"
    )
    JUNC_TYPE: int = Field(
        default=0,
        description="Junction type (0=none, 1=traffic light, 2=roundabout)",
        alias="junction_type"
    )
    SLOPE: float | None = Field(
        default=None,
        description="Road slope in percent",
        alias="slope"
    )
    
    class Config:
        """Pydantic model configuration."""
        populate_by_name = True

class TrafficFlow(BaseModel):
    """User-facing traffic flow parameters for a road segment.
    
    Required fields:
    - At least one vehicle count (light or heavy)
    - Speed for each provided vehicle count
    
    Optional fields:
    - Medium vehicles
    - Motorcycles (light and heavy)
    - All associated speeds
    """


    class Config:
        """Pydantic model configuration."""
        populate_by_name = True  # Allow both alias and field names
        alias_generator = None   # Use explicit aliases only

    def to_internal(self) -> CnossosTrafficFlow:
        """Convert to internal model."""
        return CnossosTrafficFlow.from_user_model(self)

    @model_validator(mode='after')
    def check_vehicles_and_speeds(self) -> 'TrafficFlow':
        """Validate required combinations of vehicles and speeds."""
        for period in ['day', 'evening', 'night']:
            # Check if at least one vehicle type is present
            has_light = getattr(self, f'light_vehicles_{period}') is not None
            has_heavy = getattr(self, f'heavy_vehicles_{period}') is not None
            
            if not has_light and not has_heavy:
                continue  # Skip period if no vehicles
                
            if has_light and getattr(self, f'light_speed_{period}') is None:
                raise ValueError(f"Light vehicle speed required for {period}")
                
            if has_heavy and getattr(self, f'heavy_speed_{period}') is None:
                raise ValueError(f"Heavy vehicle speed required for {period}")
                
            # Optional vehicles need speed if present
            if getattr(self, f'medium_vehicles_{period}'):
                if getattr(self, f'medium_speed_{period}') is None:
                    raise ValueError(f"Medium vehicle speed required for {period}")
                    
            # Similar checks for motorcycles...
            
        return self

    sid: int = Field(
        alias="id",
        description="Unique identifier for the road segment",
    )
    # Day period (6-18h)
    light_vehicles_day: float = Field(
        default=0.0,
        description="Light vehicles per hour (6-18h)",
        ge=0.0,
    )
    medium_vehicles_day: float | None = Field(
        default=None,
        description="Medium heavy vehicles, delivery vans > 3.5t, buses per hour (6-18h)",
        ge=0.0,
    )
    heavy_vehicles_day: float = Field(
        default=0.0,
        description="Heavy duty vehicles, buses with 3+ axles per hour (6-18h)",
        ge=0.0,
    )
    light_motorcycles_day: Optional[float] = Field(
        default=None,
        description="Mopeds, tricycles, quads ≤ 50cc per hour (6-18h)",
        ge=0.0,
    )
    heavy_motorcycles_day: Optional[float] = Field(
        default=None,
        description="Motorcycles, tricycles, quads > 50cc per hour (6-18h)",
        ge=0.0,
    )

    # Evening period (18-22h)
    light_vehicles_evening: float = Field(
        default=0.0,
        description="Light vehicles per hour (18-22h)",
        ge=0.0,
    )
    medium_vehicles_evening: float | None = Field(
        default=None,
        description="Medium heavy vehicles per hour (18-22h)",
        ge=0.0,
    )
    heavy_vehicles_evening: float = Field(
        default=0.0,
        description="Heavy duty vehicles per hour (18-22h)",
        ge=0.0,
    )
    light_motorcycles_evening: Optional[float] = Field(
        default=None,
        description="Mopeds ≤ 50cc per hour (18-22h)",
        ge=0.0,

    )
    heavy_motorcycles_evening: Optional[float] = Field(
        default=None,
        description="Motorcycles > 50cc per hour (18-22h)",
        ge=0.0,
    )

    # Night period (22-6h)
    light_vehicles_night: float = Field(
        default=0.0,
        description="Light vehicles per hour (22-6h)",
        ge=0.0,
    )
    medium_vehicles_night: float | None = Field(
        default=None,
        description="Medium heavy vehicles per hour (22-6h)",
        ge=0.0,
    )
    heavy_vehicles_night: float = Field(
        default=0.0,
        description="Heavy duty vehicles per hour (22-6h)",
        ge=0.0,
    )
    light_motorcycles_night: Optional[float] = Field(
        default=None,
        description="Mopeds ≤ 50cc per hour (22-6h)",
        ge=0.0,
    )
    heavy_motorcycles_night: Optional[float] = Field(
        default=None,
        description="Motorcycles > 50cc per hour (22-6h)",
        ge=0.0,
    )

    # Speeds
    light_speed_day: float | None = Field(
        default=None,
        description="Light vehicle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
    )
    light_speed_evening: float | None = Field(
        default=None,
        description="Light vehicle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
    )
    light_speed_night: float | None = Field(
        default=None,
        description="Light vehicle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
    )

    medium_speed_day: float | None = Field(  # Add missing speed fields
        default=None,
        description="Medium vehicle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
    )
    medium_speed_evening: float | None = Field(
        default=None,
        description="Medium vehicle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
    )
    medium_speed_night: float | None = Field(
        default=None,
        description="Medium vehicle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
    )
    heavy_speed_day: float | None = Field(
        default=None,
        description="Heavy vehicle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
    )
    heavy_speed_evening: float | None = Field(
        default=None,
        description="Heavy vehicle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
    )
    heavy_speed_night: float | None = Field(
        default=None,
        description="Heavy vehicle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
    )

    light_moto_speed_day: float | None = Field(  # Rename from wav_spd to light_moto_speed
        default=None,
        description="Moped speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
    )
    light_moto_speed_evening: float | None = Field(
        default=None,
        description="Moped speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
    )
    light_moto_speed_night: float | None = Field(
        default=None,
        description="Moped speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
    )

    heavy_moto_speed_day: float | None = Field(  # Rename from wbv_spd to heavy_moto_speed
        default=None,
        description="Motorcycle speed in km/h (6-18h)",
        ge=0.0,
        le=200.0,
    )
    heavy_moto_speed_evening: float | None = Field(
        default=None,
        description="Motorcycle speed in km/h (18-22h)",
        ge=0.0,
        le=200.0,
    )
    heavy_moto_speed_night: float | None = Field(
        default=None,
        description="Motorcycle speed in km/h (22-6h)",
        ge=0.0,
        le=200.0,
    )
    # Road properties
    pavement: str = Field(
        default="NL08",
        description="CNOSSOS road surface type (e.g. NL08)",
        pattern=r"^(NL(0[1-9]|1[0-4])|DEF)$",
    )
    
    temperature_day: float = Field(
        default=20.0,
        description="Average temperature in °C (6-18h)",
    )
    temperature_evening: float = Field(
        default=20.0,
        description="Average temperature in °C (18-22h)",
    )
    temperature_night: float = Field(
        default=20.0,
        description="Average temperature in °C (22-6h)",
    )
    
    studded_tires_months: Optional[float] = Field(
        default=None,
        description="Months per year with studded tires (0-12)",
        ge=0.0,
        le=12.0
    )
    studded_tires_ratio: Optional[float] = Field(
        default=None,
        description="Ratio of vehicles with studded tires (0-1)",
        ge=0.0,
        le=1.0,
    )
    
    junction_distance: Optional[float] = Field(
        default=None,
        description="Distance to junction in meters",
        ge=0.0,
    )
    junction_type: JunctionType = Field(
        default=JunctionType.NONE,
        description="Type of junction (0=none, 1=traffic light, 2=roundabout)",
    )
    slope: Optional[float] = Field(
        default=None,
        description="Road slope in percent",
    )

RoadsFeatureCollection = FeatureCollection[
    Feature[LineString | MultiLineString, TrafficFlow]
]

RoadsFeature = Feature[
    LineString | MultiLineString, TrafficFlow
]