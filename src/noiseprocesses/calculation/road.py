import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.types import Double, Integer, String

from noiseprocesses.calculation.emission import (
    EmissionConfig,
    EmissionSource,
)
from noiseprocesses.core.database import NoiseDatabase

logger = logging.getLogger(__name__)

@dataclass
class RoadCalculationConfig(EmissionConfig):
    """Configuration for road noise calculations."""
    coefficient_version: int = 2
    default_temp: float = 20.0
    default_pavement: str = "NL08"
    default_junction_dist: float = 100.0
    default_junction_type: int = 2
    default_way: int = 3

class RoadNoiseCalculator(EmissionSource):
    """Handles road noise emission calculations following CNOSSOS-EU."""
    
    def calculate_emissions(self, roads_table: str = "ROADS_TRAFFIC") -> str:
        """Calculate road noise emissions following CNOSSOS-EU method.
        
        Args:
            roads_table (str): Name of the table containing road data
            
        Returns:
            str: Name of the created emission table
        """
        logger.info("Starting emission calculations for %s", roads_table)
        
        # Create emission table with proper structure
        self._create_emission_table("LW_ROADS")
        
        # Get total number of roads
        road_count = self.database.query(f"SELECT COUNT(*) FROM {roads_table}")[0][0]
        logger.info("Processing %d road segments", road_count)
        
        # Prepare insert statement
        insert_sql = """
            INSERT INTO LW_ROADS (pk, the_geom,
                LWD63, LWD125, LWD250, LWD500, LWD1000, LWD2000, LWD4000, LWD8000,
                LWE63, LWE125, LWE250, LWE500, LWE1000, LWE2000, LWE4000, LWE8000,
                LWN63, LWN125, LWN250, LWN500, LWN1000, LWN2000, LWN4000, LWN8000)
            VALUES (?, ?, 
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Process roads in batches
        batch_size = 100
        for offset in range(0, road_count, batch_size):
            roads = self.database.query(f"""
                SELECT * FROM {roads_table} 
                ORDER BY PK
                LIMIT {batch_size} OFFSET {offset}
            """)
            
            batch_values = []
            for road in roads:
                # Calculate emissions using CNOSSOS
                lden_data = self.database.java_bridge.LDENPropagationProcessData(
                    None, self.lden_config
                )
                emissions = lden_data.computeLw(road)
                
                # Convert power to dB for each period
                power_utils = self.database.java_bridge.PowerUtils
                day_db = power_utils.wToDba(emissions[0])
                evening_db = power_utils.wToDba(emissions[1])
                night_db = power_utils.wToDba(emissions[2])
                
                # Prepare values for insert
                values = [
                    road['PK'], road['THE_GEOM'],
                    *day_db, *evening_db, *night_db
                ]
                batch_values.append(values)
            
            # Execute batch insert
            self.database.execute_batch(insert_sql, batch_values)
        
        # Update geometry Z value for visualization
        self.database.execute(
            "UPDATE LW_ROADS SET THE_GEOM = ST_UPDATEZ(THE_GEOM, 0.05)"
        )
        
        # Add primary key constraint
        self.database.add_primary_key("LW_ROADS")
        
        logger.info("Emission calculation completed")
        return "LW_ROADS"
