# implements PropagationCalculator
import logging

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.core.java_bridge import JavaBridge
from noiseprocesses.models.noise_calculation_config import (
    NoiseCalculationConfig,
    OutputIsoSurfaces,
)

logger = logging.getLogger(__name__)


class RoadPropagationCalculator:
    """Handles road noise propagation calculations following CNOSSOS-EU."""

    def __init__(
        self,
        database: NoiseDatabase,
    ):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()

    def calculate_propagation(self, config: NoiseCalculationConfig) -> str:
        """Calculate noise propagation using NoiseModelling.

        Args:
            emission_table: Table containing emission points
            receivers_table: Table containing receiver points
            buildings_table: Table containing building geometries
            dem_table: Optional DEM table name
            ground_table: Optional ground absorption table name

        Returns:
            str: Name of the main output table (LDEN_GEOM)
        """
        logger.info("Starting propagation calculation")

        try:
            # Initialize LDEN factory with config
            lden_config = self.java_bridge.LDENConfig(
                self.java_bridge.LDENConfig.INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
            )

            # need to convert from dict to boolean values: presence means True
            output_controls = {
                OutputIsoSurfaces.noise_day: OutputIsoSurfaces.noise_day
                in config.output_controls,
                OutputIsoSurfaces.noise_evening: OutputIsoSurfaces.noise_evening
                in config.output_controls,
                OutputIsoSurfaces.noise_night: OutputIsoSurfaces.noise_night
                in config.output_controls,
                OutputIsoSurfaces.noise_den: OutputIsoSurfaces.noise_den
                in config.output_controls,
            }

            # Configure output tables
            lden_config.setComputeLDay(
                output_controls.get(OutputIsoSurfaces.noise_day)
            )
            lden_config.setComputeLEvening(
                output_controls.get(OutputIsoSurfaces.noise_evening)
            )
            lden_config.setComputeLNight(
                output_controls.get(OutputIsoSurfaces.noise_night)
            )
            lden_config.setComputeLDEN(
                output_controls.get(OutputIsoSurfaces.noise_den)
            )
            lden_config.setMergeSources(
                not config.additional_output_controls.export_source_id
            )

            # Initialize noise map calculator
            noise_map = self.java_bridge.PointNoiseMap(
                config.required_input.building_table,
                config.required_input.roads_table,
                config.required_input.receivers_table,
            )
            noise_map.setHeightField("HEIGHT")

            # Configure acoustic parameters
            params = config.acoustic_params
            noise_map.setWallAbsorption(params.wall_alpha)
            noise_map.setMaximumPropagationDistance(params.max_source_distance)
            noise_map.setMaximumReflectionDistance(params.max_reflection_distance)
            noise_map.setSoundReflectionOrder(params.reflection_order)

            # Configure propagation settings
            settings = config.propagation_settings
            noise_map.setComputeHorizontalDiffraction(settings.horizontal_diffraction)
            noise_map.setComputeVerticalDiffraction(settings.vertical_diffraction)

            # Set optional DEM and ground absorption
            if dem_table := config.optional_input.dem_table:
                noise_map.setDemTable(dem_table)
            if ground_table := config.optional_input.ground_absorption_table:
                noise_map.setSoilTableName(ground_table)

            # Configure environmental conditions
            self._configure_environmental_data(noise_map, config)

            # Set performance parameters
            noise_map.setThreadCount(config.performance.thread_count)
            noise_map.setMaximumError(0.1)  # Maximum allowed error in dB

            # Create LDEN processor
            lden_processor = self.java_bridge.LDENPointNoiseMapFactory(
                self.database.connection, lden_config
            )
            noise_map.setComputeRaysOutFactory(lden_processor)
            noise_map.setPropagationProcessDataFactory(lden_processor)

            progressLogger = self.java_bridge.RootProgressVisitor(1, True, 1)

            # Create profiler
            now = self.java_bridge.LocalDateTime.now()
            profile_file = self.java_bridge.File(
                f"profile_{now.getYear()}_{now.getMonthValue()}_{now.getDayOfMonth()}_{now.getHour()}h{now.getMinute()}.csv"
            )
            profiler_thread = self.java_bridge.ProfilerThread(profile_file)

            # Add metrics
            profiler_thread.addMetric(lden_processor)
            profiler_thread.addMetric(self.java_bridge.ProgressMetric(progressLogger))
            profiler_thread.addMetric(self.java_bridge.JVMMemoryMetric())
            profiler_thread.addMetric(self.java_bridge.ReceiverStatsMetric())

            # Configure intervals
            profiler_thread.setWriteInterval(300)
            profiler_thread.setFlushInterval(300)

            # Attach to noise map
            noise_map.setProfilerThread(profiler_thread)

            # Initialize calculation
            empty_visitor = self.java_bridge.EmptyProgressVisitor()
            noise_map.initialize(self.database.connection, empty_visitor)

            # Run calculation with progress tracking
            progress_visitor = self.java_bridge.RootProgressVisitor(1, True, 1)
            receivers = self.java_bridge.HashSet()  # Track processed receivers

            try:
                lden_processor.start()

                cells = noise_map.searchPopulatedCells(self.database.connection)

                for index, cell_index in enumerate(sorted(cells.keySet())):
                    progress = 100 * index / cells.size()
                    logger.info(
                        f"Compute... {progress:.3f} % ({cells.get(cell_index)} receivers in this cell)"
                    )
                    noise_map.evaluateCell(
                        self.database.connection,
                        cell_index.getLatitudeIndex(),
                        cell_index.getLongitudeIndex(),
                        progress_visitor,
                        receivers,
                    )
            finally:
                lden_processor.stop()

            # Get receiver geometry field
            geom_fields = self.database.query(f"""
                SELECT f_geometry_column 
                FROM geometry_columns 
                WHERE f_table_name = '{config.required_input.receivers_table.upper()}'
            """)

            if not geom_fields:
                raise ValueError("No geometry column found in receivers table")

            # Create final tables with geometry
            created_tables = self._create_result_tables(
                lden_config, config.required_input.receivers_table, geom_fields[0][0]
            )

            logger.info(
                f"Calculation complete. Created tables: {', '.join(created_tables)}"
            )
            return "LDEN_GEOM"

        except Exception as e:
            logger.error(f"Propagation calculation failed: {str(e)}")
            raise

    def _init_noise_map(
        self, buildings_table: str, emission_table: str, receivers_table: str
    ):
        """Initialize PointNoiseMap object."""
        noise_map = self.java_bridge.PointNoiseMap(
            buildings_table, emission_table, receivers_table
        )
        noise_map.setHeightField("HEIGHT")  # Set building height field
        return noise_map

    def _configure_lden(self, config):
        """Configure LDEN calculation settings."""
        lden_config = self.java_bridge.LDENConfig(
            self.java_bridge.LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
        )

        output = config.output_controls
        lden_config.setComputeLDay(not output.skip_lday)
        lden_config.setComputeLEvening(not output.skip_levening)
        lden_config.setComputeLNight(not output.skip_lnight)
        lden_config.setComputeLDEN(not output.skip_lden)
        lden_config.setMergeSources(not output.export_source_id)

        return lden_config

    def _configure_environmental_data(self, noise_map, config: NoiseCalculationConfig):
        """Configure environmental conditions for each period."""
        PropagationProcessPathData = self.java_bridge.PropagationProcessPathData
        LDENConfig = self.java_bridge.LDENConfig

        # Initialize environmental data for each period
        env_day = PropagationProcessPathData(False)
        env_evening = PropagationProcessPathData(False)
        env_night = PropagationProcessPathData(False)

        # Set base parameters
        for env_data in [env_day, env_evening, env_night]:
            env_data.setHumidity(config.acoustic_params.humidity)
            env_data.setTemperature(config.acoustic_params.temperature)

        # Configure favorable occurrences for each period
        if favorable_day := config.propagation_settings.favorable_day:
            self._set_wind_rose(env_day, favorable_day)

        if config.propagation_settings.favorable_evening:
            self._set_wind_rose(
                env_evening, config.propagation_settings.favorable_evening
            )

        if config.propagation_settings.favorable_night:
            self._set_wind_rose(env_night, config.propagation_settings.favorable_night)

        # Set environmental data for each period
        noise_map.setPropagationProcessPathData(LDENConfig.TIME_PERIOD.DAY, env_day)
        noise_map.setPropagationProcessPathData(
            LDENConfig.TIME_PERIOD.EVENING, env_evening
        )
        noise_map.setPropagationProcessPathData(LDENConfig.TIME_PERIOD.NIGHT, env_night)

    def _set_wind_rose(self, env_data, occurrences_str: str):
        """Set wind rose data for environmental configuration.

        Args:
            env_data: PropagationProcessPathData instance
            occurrences_str: Comma-separated string of occurrence values
        """
        try:
            # Convert string to float values
            occurrences = [float(val.strip()) for val in occurrences_str.split(",")]

            # Ensure correct length
            default_length = len(
                self.java_bridge.PropagationProcessPathData.DEFAULT_WIND_ROSE
            )
            if len(occurrences) != default_length:
                raise ValueError(
                    f"Expected {default_length} values for wind rose, "
                    f"got {len(occurrences)}"
                )

            # Clamp values between 0 and 1
            occurrences = [max(0.0, min(1.0, val)) for val in occurrences]

            # Set wind rose data
            env_data.setWindRose(occurrences)

        except Exception as e:
            logger.error(f"Failed to set wind rose data: {e}")
            raise

    def _create_result_tables(
        self, lden_config, receivers_table: str, receivers_geom_field: str
    ) -> list[str]:
        """Create final result tables with geometry.

        Args:
            lden_config: LDEN configuration from NoiseModelling java class
            receivers_table: Name of receivers table
            receivers_geom_field: Name of geometry field in receivers table

        Returns:
            List of created table names
        """
        logger.info("Creating result tables with geometry")
        created_tables = []

        # Helper function to create and populate table
        def create_period_table(name: str, source_table: str):
            """Create result table for time period."""
            # Drop existing table
            self.database.execute(f"DROP TABLE IF EXISTS {name}")

            # Build base column definition
            columns = []
            if not lden_config.isMergeSources():
                columns.extend(
                    ["IDRECEIVER BIGINT NOT NULL", "IDSOURCE BIGINT NOT NULL"]
                )
            else:
                columns.append("IDRECEIVER BIGINT NOT NULL")

            columns.append("THE_GEOM GEOMETRY")

            # Add frequency columns
            path_data = lden_config.getPropagationProcessPathData(
                self.java_bridge.LDENConfig.TIME_PERIOD.DAY
            )
            for freq in path_data.freq_lvl:
                columns.append(f"HZ{freq} NUMERIC(5,2)")

            # Add level columns
            columns.extend(["LAEQ NUMERIC(5,2)", "LEQ NUMERIC(5,2)"])

            # Build SELECT columns
            select_columns = [
                "r.PK AS IDRECEIVER",
                f"r.{receivers_geom_field} AS THE_GEOM",
            ]
            if not lden_config.isMergeSources():
                select_columns.append("s.IDSOURCE")

            # Add frequency and level columns to SELECT
            select_columns.extend([f"s.HZ{freq}" for freq in path_data.freq_lvl])
            select_columns.extend(["s.LAEQ", "s.LEQ"])

            # Create table with data
            self.database.execute(f"""
                CREATE TABLE {name} (
                    {", ".join(columns)}
                ) AS 
                SELECT {", ".join(select_columns)}
                FROM {receivers_table} r
                {"LEFT" if lden_config.isMergeSources() else ""} JOIN {source_table} s 
                ON r.PK = s.IDRECEIVER
            """)

            # Add primary key
            pk_columns = ["IDRECEIVER"]
            if not lden_config.isMergeSources():
                pk_columns.append("IDSOURCE")
            self.database.execute(
                f"ALTER TABLE {name} ADD PRIMARY KEY ({','.join(pk_columns)})"
            )

        # Create tables for each time period if configured
        if lden_config.isComputeLDay():
            create_period_table("LDAY_GEOM", lden_config.getlDayTable())

        if lden_config.isComputeLEvening():
            create_period_table("LEVENING_GEOM", lden_config.getlEveningTable())

        if lden_config.isComputeLNight():
            create_period_table("LNIGHT_GEOM", lden_config.getlNightTable())

        if lden_config.isComputeLDEN():
            create_period_table("LDEN_GEOM", lden_config.getlDenTable())

        return created_tables
