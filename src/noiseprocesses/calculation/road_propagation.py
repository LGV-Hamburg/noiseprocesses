# implements PropagationCalculator
from noiseprocesses.core.database import NoiseDatabase

from dataclasses import dataclass
from typing import Optional
import logging

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.protocols import PropagationCalculator

logger = logging.getLogger(__name__)

@dataclass
class PropagationConfig:
    """Configuration for noise propagation calculation"""
    wall_alpha: float = 0.1
    max_src_dist: float = 150.0
    max_refl_dist: float = 50.0
    reflection_order: int = 1
    thread_count: int = 0
    vertical_diffraction: bool = False
    horizontal_diffraction: bool = False
    humidity: float = 70.0
    temperature: float = 15.0
    favorable_occurrences: dict[str, list[float]] = None

    def __post_init__(self):
        if self.favorable_occurrences is None:
            # Default 0.5 probability for each direction/period
            self.favorable_occurrences = {
                "day": [0.5] * 16,
                "evening": [0.5] * 16,
                "night": [0.5] * 16
            }

class RoadPropagationCalculator:
    """Handles road noise propagation calculations following CNOSSOS-EU."""
    
    def __init__(
        self, 
        database: NoiseDatabase,
        config: Optional[PropagationConfig] = None
    ):
        self.database = database
        self.config = config or PropagationConfig()

    def calculate_propagation(
        self,
        emission_table: str,
        receivers_table: str,
        buildings_table: str,
        dem_table: str | None = None,
        ground_table: str | None = None,
        output_tables: list[str] | None = None
    ) -> None:
        """Calculate noise propagation using NoiseModelling."""
        
        logger.info("Starting propagation calculation")
        
        # Get Java classes
        PointNoiseMap = self.database.java_bridge.PointNoiseMap
        LDENConfig = self.database.java_bridge.LDENConfig
        PropagationProcessPathData = self.database.java_bridge.PropagationProcessPathData
        
        # Initialize noise map calculator
        noise_map = PointNoiseMap(buildings_table, emission_table, receivers_table)
        
        # Configure LDEN calculation
        lden_config = LDENConfig(LDENConfig.INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW)
        if output_tables:
            lden_config.setComputeLDay("LDAY_GEOM" in output_tables)
            lden_config.setComputeLEvening("LEVENING_GEOM" in output_tables)
            lden_config.setComputeLNight("LNIGHT_GEOM" in output_tables)
            lden_config.setComputeLDEN("LDEN_GEOM" in output_tables)
            
        # Setup environmental data for each period
        env_data = PropagationProcessPathData(False)
        env_data.setHumidity(self.config.humidity)
        env_data.setTemperature(self.config.temperature)
        
        for period, occurrences in self.config.favorable_occurrences.items():
            period_env = PropagationProcessPathData(env_data)
            period_env.setFavorableOccurrencesInPercent(occurrences)
            noise_map.setPropagationProcessPathData(
                getattr(LDENConfig.TIME_PERIOD, period.upper()),
                period_env
            )
            
        # Configure propagation parameters
        noise_map.setComputeHorizontalDiffraction(self.config.horizontal_diffraction)
        noise_map.setComputeVerticalDiffraction(self.config.vertical_diffraction)
        noise_map.setSoundReflectionOrder(self.config.reflection_order)
        noise_map.setWallAbsorption(self.config.wall_alpha)
        noise_map.setMaximumPropagationDistance(self.config.max_src_dist)
        noise_map.setMaximumReflectionDistance(self.config.max_refl_dist)
        noise_map.setThreadCount(self.config.thread_count)
        
        # Set optional DEM and ground absorption
        if dem_table:
            noise_map.setDemTable(dem_table)
        if ground_table:
            noise_map.setGroundAbsorptionTable(ground_table)
            
        # Initialize and run calculation
        progress_visitor = self.database.java_bridge.RootProgressVisitor(1, True, 1)
        noise_map.initialize(self.database.connection, progress_visitor)
        noise_map.computeNoisePropagation(progress_visitor)
