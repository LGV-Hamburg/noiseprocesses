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
        table_name = "LW_ROADS"
        self._create_emission_table(table_name)
        
        # Get total number of roads
        road_count = self.database.query(f"SELECT COUNT(*) FROM {roads_table}")[0][0]
        logger.info("Processing %d road segments", road_count)
        
        # Generate column names for insert statement
        emission_columns = [
            f'LW{period}{freq}'
            for period in self.config.TIME_PERIODS
            for freq in self.config.FREQUENCY_BANDS
        ]
        
        # Create insert statement dynamically
        insert_sql = f"""
            INSERT INTO {table_name} (pk, the_geom, {', '.join(emission_columns)})
            VALUES ({', '.join(['?'] * (len(emission_columns) + 2))})
        """

        # Get Java classes
        SpatialResultSet = self.database.java_bridge.SpatialResultSet
        # SpatialResultSetWrapper = self.database.java_bridge.SpatialResultSetWrapper
        
        # Process roads in batches
        batch_size = 100
        for offset in range(0, road_count, batch_size):
            # Use statement to get SpatialResultSet
            statement = self.database.connection.createStatement()
            try:
                result = statement.executeQuery(f"""
                    SELECT * FROM {roads_table} 
                    ORDER BY PK
                    LIMIT {batch_size} OFFSET {offset}
                """)

                # Cast ResultSet to SpatialResultSet
                spatial_result = result.unwrap(SpatialResultSet)
                
                batch_values = []
                while result.next():
                    # Calculate emissions using CNOSSOS with SpatialResultSet
                    lden_data = self.database.java_bridge.LDENPropagationProcessData(
                        None, self.lden_config
                    )
                    emissions = lden_data.computeLw(spatial_result)
                    
                    # Convert power to dB for each period
                    power_utils = self.database.java_bridge.PowerUtils
                    day_db = power_utils.wToDba(emissions[0])
                    evening_db = power_utils.wToDba(emissions[1])
                    night_db = power_utils.wToDba(emissions[2])
                    
                    # Prepare values for insert
                    values = [
                        spatial_result.getInt("PK"),
                        spatial_result.getObject("THE_GEOM"),
                        *day_db, *evening_db, *night_db
                    ]
                    batch_values.append(values)
                    
                # Execute batch insert
                self.database.execute_batch(insert_sql, batch_values)
                
            finally:
                statement.close()
        
        # Update geometry Z value for visualization
        self.database.execute(
            "UPDATE LW_ROADS SET THE_GEOM = ST_UPDATEZ(THE_GEOM, 0.05)"
        )
        
        # Add primary key constraint
        self.database.add_primary_key("LW_ROADS")
        
        logger.info("Emission calculation completed")
        return "LW_ROADS"
