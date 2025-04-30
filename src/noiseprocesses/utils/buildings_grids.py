import logging

from noiseprocesses.core.java_bridge import JavaBridge
from noiseprocesses.core.database import NoiseDatabase, SQLBuilder
from noiseprocesses.models.grid_config import (
    BuildingGridConfig2d, BuildingGridConfig3d
)

from noiseprocesses.utils import srid

logger = logging.getLogger(__name__)


class BuildingGridGenerator2d:
    """Generates a 2D grid of receivers around building facades"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0

    def generate_receivers(self, config: BuildingGridConfig2d) -> str:
        """
        Generate a 2D grid of receivers around building facades.

        Args:
            config: Configuration for grid generation.

        Returns:
            str: Name of the created receivers table.
        """
        logger.info("Starting 2D building grid generation")

        # Get SRID from input tables
        self.target_srid = srid.get_srid(
            self.database,
            self.java_bridge,
            config
        )

        # Drop existing tables
        self.database.execute(SQLBuilder.drop_table(config.output_table))

        # Create temporary table for receiver lines
        logger.info("Creating receiver lines")
        self.database.execute(SQLBuilder.drop_table("tmp_receivers_lines"))
        self.database.execute(
            f"""
            CREATE TABLE tmp_receivers_lines(pk INT NOT NULL PRIMARY KEY, the_geom GEOMETRY) AS
            SELECT
                b.pk AS pk,
                ST_SimplifyPreserveTopology(
                    ST_ToMultiLine(ST_Buffer(b.the_geom, {config.distance_from_wall}, 'join=bevel')),
                    0.05
                ) AS the_geom
            FROM {config.buildings_table} b
            """
        )
        self.database.execute("CREATE SPATIAL INDEX ON tmp_receivers_lines(the_geom)")

        # identify buildings whose heights exceed the 
        # receiver height (overlapping buildings)
        logger.info(
            "Identifying buildings that intersect "
            "receiver lines and are taller than the receiver height"
        )
        self.database.execute(SQLBuilder.drop_table("tmp_relation_screen_building"))
        self.database.execute(
            f"""
            CREATE TABLE tmp_relation_screen_building AS
            SELECT
                b.pk AS PK_building,
                s.pk AS pk_screen
            FROM {config.buildings_table} b
            JOIN tmp_receivers_lines s
            ON ST_Intersects(b.the_geom, s.the_geom)
            WHERE b.pk != s.pk
            AND b.height > {config.calculation_height}
            """
        )

        # Add indexes for performance
        self.database.execute(
            SQLBuilder.create_index("tmp_relation_screen_building", "pk_screen")
        )
        self.database.execute(
            SQLBuilder.create_index("tmp_relation_screen_building", "pk_building")
        )

        # Truncate receiver lines if they overlap with buildings
        logger.info("Truncating receiver lines")
        self.database.execute(SQLBuilder.drop_table("tmp_screen_truncated"))
        self.database.execute(
            f"""
            CREATE TABLE tmp_screen_truncated(
                pk_screen INT NOT NULL,
                the_geom GEOMETRY
            ) AS
            SELECT
                r.pk_screen,
                ST_Difference(
                    s.the_geom,
                    ST_Buffer(ST_Accum(b.the_geom), {config.distance_from_wall})
                ) AS the_geom
            FROM tmp_relation_screen_building r
            JOIN {config.buildings_table} b ON ON r.PK_building = b.PK_building
            JOIN tmp_receivers_lines s ON r.pk_screen = s.pk
            GROUP BY r.pk_screen, s.the_geom
            """
        )
        self.database.execute(
            SQLBuilder.create_index("tmp_screen_truncated", "pk_screen")
        )

        # Merge truncated and non-truncated lines
        logger.info("Merging truncated and non-truncated receiver lines")
        self.database.execute("DROP TABLE IF EXISTS TMP_SCREENS_MERGE")
        self.database.execute(
            """
            CREATE TABLE TMP_SCREENS_MERGE(
                pk INT NOT NULL,
                the_geom GEOMETRY
            ) AS
            SELECT
                s.pk,
                s.the_geom
            FROM tmp_receivers_lines s
            WHERE NOT ST_IsEmpty(s.the_geom)
              AND s.pk NOT IN (SELECT pk_screen FROM tmp_screen_truncated)
            UNION ALL
            SELECT
                pk_screen,
                the_geom
            FROM tmp_screen_truncated
            WHERE NOT ST_IsEmpty(the_geom)
            """
        )
        self.database.execute("ALTER TABLE TMP_SCREENS_MERGE ADD PRIMARY KEY(pk)")

        # Convert lines to points
        logger.info("Converting lines to points")
        self.database.execute(
            f"""
            CREATE TABLE {config.output_table} AS
            SELECT
                ST_SetSRID(ST_PointN(the_geom, generate_series(1, ST_NumPoints(the_geom))), {self.target_srid}) AS the_geom
            FROM tmp_receivers_lines
            """
        )
        self.database.execute(f"CREATE SPATIAL INDEX ON {config.output_table}(the_geom)")

        logger.info(f"2D building grid generation completed: {config.output_table}")
        return config.output_table


class BuildingGridGenerator3d:
    """Generates a 3D grid of receivers around building facades"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0

    def generate_receivers(self, config: BuildingGridConfig3d) -> str:
        """
        Generate a 3D grid of receivers around building facades.

        Args:
            config: Configuration for grid generation.

        Returns:
            str: Name of the created receivers table.
        """
        logger.info("Starting 3D building grid generation")

        # Get SRID from input tables
        self.target_srid = srid.get_srid(
            self.database,
            self.java_bridge,
            config
        )

        # Drop existing tables
        self.database.execute(SQLBuilder.drop_table(config.output_table))

        # Create temporary table for receiver lines
        logger.info("Creating receiver lines")
        self.database.execute(
            f"""
            CREATE TABLE tmp_receivers_lines AS
            SELECT
                b.pk AS building_pk,
                ST_SimplifyPreserveTopology(
                    ST_ToMultiLine(ST_Buffer(b.the_geom, {config.distance_from_wall}, 'join=bevel')),
                    0.05
                ) AS the_geom,
                b.height AS building_height
            FROM {config.buildings_table} b
            """
        )
        self.database.execute("CREATE SPATIAL INDEX ON tmp_receivers_lines(the_geom)")

        # Generate 3D points
        logger.info("Generating 3D points")
        self.database.execute(
            f"""
            CREATE TABLE {config.output_table} AS
            SELECT
                ST_SetSRID(
                    ST_MakePoint(
                        ST_X(the_geom),
                        ST_Y(the_geom),
                        generate_series(1.5, building_height, {config.height_between_levels})
                    ),
                    {self.target_srid}
                ) AS the_geom
            FROM tmp_receivers_lines
            """
        )
        self.database.execute(f"CREATE SPATIAL INDEX ON {config.output_table}(the_geom)")

        logger.info(f"3D building grid generation completed: {config.output_table}")
        return config.output_table
