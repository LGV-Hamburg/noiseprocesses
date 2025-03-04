import logging
from typing import Any

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.types import Double, Integer, String

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.emission_config import RoadEmissionConfig as EmissionConfig

logger = logging.getLogger(__name__)


class RoadEmissionCalculator:
    """Handles road noise emission calculations following CNOSSOS-EU."""

    def __init__(self, database: NoiseDatabase, config: EmissionConfig | None = None):
        self.database = database
        self.emission_config = config or EmissionConfig()
        self.metadata = MetaData()

        # Initialize NoiseModelling config
        self.lden_config = self._init_lden_config()

    def _init_lden_config(self) -> Any:
        """Initialize LDEN configuration."""
        # Get required Java classes
        LDENConfig = self.database.java_bridge.LDENConfig
        LDENConfig_INPUT_MODE = self.database.java_bridge.LDENConfig_INPUT_MODE
        LDENConfig_TIME_PERIOD = self.database.java_bridge.LDENConfig_TIME_PERIOD
        PropagationProcessPathData = (
            self.database.java_bridge.PropagationProcessPathData
        )

        # Initialize config with traffic flow mode
        lden_config = LDENConfig(LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW)
        lden_config.setCoefficientVersion(self.emission_config.coefficient_version)

        # Configure periods without propagation
        period_map = {
            "DAY": LDENConfig_TIME_PERIOD.DAY,
            "EVENING": LDENConfig_TIME_PERIOD.EVENING,
            "NIGHT": LDENConfig_TIME_PERIOD.NIGHT,
        }

        for java_period in period_map.values():
            lden_config.setPropagationProcessPathData(
                java_period, PropagationProcessPathData(False)
            )

        return lden_config

    def calculate_emissions(self, source_table: str = "ROADS_TRAFFIC") -> str:
        """Calculate road noise emissions following CNOSSOS-EU method.

        Args:
            roads_table (str): Name of the table containing road data

        Returns:
            str: Name of the created emission table
        """
        logger.info("Starting emission calculations for %s", source_table)

        # Create emission table with proper structure
        roads_table_emissions = "LW_ROADS"
        self._create_emission_table(roads_table_emissions)

        # Configure processing sizes
        batch_size = 100
        chunk_size = 5000  # Process larger chunks for better memory management

        # Get total number of roads
        road_count = self.database.query(f"SELECT COUNT(*) FROM {source_table}")[0][0]
        logger.info("Processing %d road segments", road_count)

        # Generate column names for insert statement
        emission_columns = [
            f"LW{period.value}{freq}"
            for period in self.emission_config.time_periods
            for freq in self.emission_config.frequency_bands
        ]

        # Create insert statement dynamically
        insert_sql = f"""
            INSERT INTO {roads_table_emissions} (pk, the_geom, {", ".join(emission_columns)})
            VALUES ({", ".join(["?"] * (len(emission_columns) + 2))})
        """

        # Get Java classes
        SpatialResultSet = self.database.java_bridge.SpatialResultSet

        # Process roads in chunks
        for chunk_offset in range(0, road_count, chunk_size):
            chunk_limit = min(chunk_size, road_count - chunk_offset)

            # Disable auto-commit for chunk processing
            old_autocommit = self.database.connection.getAutoCommit()
            self.database.connection.setAutoCommit(False)

            try:
                # Process roads in batches within chunk
                for batch_offset in range(0, chunk_limit, batch_size):
                    statement = self.database.connection.createStatement()
                    try:
                        result = statement.executeQuery(f"""
                            SELECT * FROM {source_table} 
                            ORDER BY PK
                            LIMIT {batch_size} 
                            OFFSET {chunk_offset + batch_offset}
                        """)

                        # Cast ResultSet to SpatialResultSet
                        spatial_result = result.unwrap(SpatialResultSet)

                        batch_values = []
                        while result.next():
                            # Calculate emissions using CNOSSOS
                            lden_data = (
                                self.database.java_bridge.LDENPropagationProcessData(
                                    None, self.lden_config
                                )
                            )
                            emissions = lden_data.computeLw(spatial_result)

                            # Convert power to dB
                            power_utils = self.database.java_bridge.PowerUtils
                            day_db = power_utils.wToDba(emissions[0])
                            evening_db = power_utils.wToDba(emissions[1])
                            night_db = power_utils.wToDba(emissions[2])

                            # Prepare values for insert
                            values = [
                                spatial_result.getInt("PK"),
                                spatial_result.getObject("THE_GEOM"),
                                *day_db,
                                *evening_db,
                                *night_db,
                            ]
                            batch_values.append(values)

                        # Execute batch insert
                        self.database.execute_batch(insert_sql, batch_values)

                    finally:
                        statement.close()

                # Commit chunk and clear cache
                self.database.connection.commit()
                if chunk_offset % (chunk_size * 5) == 0:
                    self.database.execute("CHECKPOINT SYNC")

            finally:
                self.database.connection.setAutoCommit(old_autocommit)

        # Update geometry Z value for visualization
        self.database.execute(
            "UPDATE LW_ROADS SET THE_GEOM = ST_UPDATEZ(THE_GEOM, 0.05)"
        )

        # Add primary key constraint
        self.database.add_primary_key("LW_ROADS")

        # After all inserts are complete and before queries
        if road_count > 10000:  # Only optimize for large datasets
            self.database.create_spatial_index(roads_table_emissions)
            self.database.optimize_table(roads_table_emissions)

        logger.info("Emission calculation completed")
        return "LW_ROADS"

    def _create_emission_table(self, table_name: str) -> None:
        """Create standardized emission table using SQLAlchemy."""
        # Define table structure
        emission_table = Table(
            table_name,
            self.metadata,
            Column("PK", Integer),
            Column("THE_GEOM", String),  # H2GIS GEOMETRY type maps to String
            *[
                Column(f"LW{period.value}{freq}", Double)
                for period in self.emission_config.time_periods
                for freq in self.emission_config.frequency_bands
            ],
        )

        # Create table using existing method
        self._create_table(emission_table)

    def _create_table(self, table: Table) -> None:
        """Create a database table from SQLAlchemy definition."""
        columns = [f"{col.name} {col.type.compile()}" for col in table.columns]
        self.database.execute(f"""
            DROP TABLE IF EXISTS {table.name};
            CREATE TABLE {table.name} (
                {",".join(columns)}
            )
        """)
