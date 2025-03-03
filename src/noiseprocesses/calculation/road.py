import logging

from noiseprocesses.calculation.emission import EmissionSource

logger = logging.getLogger(__name__)


class RoadNoiseCalculator(EmissionSource):
    """Handles road noise emission calculations following CNOSSOS-EU."""

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
