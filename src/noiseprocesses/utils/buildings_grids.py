import logging
import math

from noiseprocesses.core.database import NoiseDatabase, SQLBuilder
from noiseprocesses.core.java_bridge import JavaBridge
from noiseprocesses.models.grid_config import BuildingGridConfig
from noiseprocesses.utils import line_to_points as ltp
from noiseprocesses.utils import srid

logger = logging.getLogger(__name__)


class BuildingGridGenerator2d:
    """Generates a 2D grid of receivers around building facades"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0

    def generate_receivers(self, config: BuildingGridConfig) -> str:
        """
        Generate a 2D grid of receivers around building facades.

        Args:
            config: Configuration for grid generation.

        Returns:
            str: Name of the created receivers table.
        """
        logger.info("Starting 2D building grid generation")

        # Get SRID from input tables
        self.target_srid = srid.get_srid(self.database, self.java_bridge, config)

        # Drop existing tables
        self.database.execute(SQLBuilder.drop_table(config.receivers_table_name))

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
            AND b.height > {config.receiver_height}
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
            JOIN {config.buildings_table} b ON r.PK_building = b.PK
            JOIN tmp_receivers_lines s ON r.pk_screen = s.pk
            GROUP BY r.pk_screen, s.the_geom;
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
            CREATE TABLE 63(
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

        logger.info("Splitting lines into points and populating TMP_SCREENS")
        self.database.execute(SQLBuilder.drop_table("TMP_SCREENS"))
        self.database.execute(
            """
            CREATE TABLE TMP_SCREENS(
                pk INT NOT NULL,
                the_geom GEOMETRY
            )
            """
        )

        # Populate TMP_SCREENS with points
        batch = []
        for row in self.database.query("SELECT pk, the_geom FROM TMP_SCREENS_MERGE"):
            pk, geom = row[0], row[1]
            points = ltp.split_line_to_points(geom, config.receiver_distance)
            for point in points:
                # Extract x, y from the point
                x, y = point.x, point.y

                # Filter out NaN coordinates
                if math.isnan(x) or math.isnan(y):
                    continue

                # Add the receiver height as the z value
                z = config.receiver_height

                # Insert the point into TMP_SCREENS
                batch.append((pk, x, y, z, self.target_srid))

        # Execute the batch insert
        self.database.execute_batch(
            "INSERT INTO TMP_SCREENS(pk, the_geom) VALUES (?, ST_SetSRID(ST_MakePoint(?, ?, ?), ?))",
            batch,
        )

        logger.info("Finally, creating RECEIVERS table...")
        # Create the RECEIVERS table
        self.database.execute(
            f"""
            CREATE TABLE {config.receivers_table_name}(
                pk INT NOT NULL AUTO_INCREMENT,
                the_geom GEOMETRY,
                build_pk INT
            )
            """
        )

        # Insert data into the RECEIVERS table
        self.database.execute(
            f"""
            INSERT INTO {config.receivers_table_name}(the_geom, build_pk)
            SELECT
                ST_SetSRID(the_geom, {self.target_srid}),
                pk AS build_pk
            FROM TMP_SCREENS
            """
        )

        logger.info("Add primary key to the RECEIVERS table")
        self.database.execute(
            f"ALTER TABLE {config.receivers_table_name} ADD PRIMARY KEY(pk)"
        )

        logger.info(
            f"2D building grid generation completed: {config.receivers_table_name}"
        )
        return config.receivers_table_name


class BuildingGridGenerator3d:
    """Generates a 3D grid of receivers around building facades"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0

    def generate_receivers(self, config: BuildingGridConfig) -> str:
        """
        Generate a 3D grid of receivers around building facades.

        Args:
            config: Configuration for grid generation.

        Returns:
            str: Name of the created receivers table.
        """
        logger.info("Starting 3D building grid generation")

        # Get SRID from input tables
        self.target_srid = srid.get_srid(self.database, self.java_bridge, config)

        # Drop existing tables
        self.database.execute(SQLBuilder.drop_table(config.receivers_table_name))

        # Create temporary table for receiver lines
        logger.info("Creating receiver lines")
        self.database.execute(SQLBuilder.drop_table("tmp_receivers_lines"))
        self.database.execute(
            f"""
            CREATE TABLE tmp_receivers_lines AS
            SELECT
                b.pk AS building_pk,
                ST_SimplifyPreserveTopology(
                    ST_ToMultiLine(
                        ST_Buffer(b.the_geom, {config.distance_from_wall}, 'join=bevel')
                    ),
                    0.05
                ) AS the_geom,
                b.height
            FROM {config.buildings_table} b
            """
        )
        self.database.execute(SQLBuilder.create_spatial_index("tmp_receivers_lines"))

        self.database.execute(SQLBuilder.drop_table("TMP_SCREENS_MERGE"))
        self.database.execute(
            """
            CREATE TABLE TMP_SCREENS_MERGE(
                the_geom GEOMETRY,
                hBuilding float,
                pk_building integer
            ) AS
            SELECT
                s.the_geom,
                s.height,
                s.pk_building
            FROM tmp_receivers_lines s
            WHERE NOT ST_IsEmpty(s.the_geom);
            """
        )
        self.database.execute("ALTER TABLE TMP_SCREENS_MERGE ADD PRIMARY KEY(pk)")

        self.database.execute(SQLBuilder.drop_table("TMP_SCREENS"))
        self.database.execute(
            """
            CREATE TABLE TMP_SCREENS(
                pk INT NOT NULL,
                the_geom GEOMETRY,
                level int,
                pk_building int
            )
            """
        )

        # Populate TMP_SCREENS with points
        batch = []
        for row in self.database.query(
            "SELECT pk, the_geom, hBuilding FROM TMP_SCREENS_MERGE"
        ):
            pk, geom, building_height = row[0], row[1], row[2]

            points = ltp.split_line_to_points(geom, config.receiver_distance)
            for point in points:
                # Extract x, y from the point
                x, y = point.x, point.y

                nLevels = math.ceil(
                    (building_height - 1.5) / config.height_between_levels
                )

                if building_height > 1.5:
                    for i in range(nLevels):
                        for point in points:
                            # Extract x, y from the point
                            x, y = point.x, point.y

                            # Filter out NaN coordinates
                            if math.isnan(x) or math.isnan(y):
                                continue

                            # Add the receiver height as the z value
                            z = 1.5 + (i * config.height_between_levels)

                            # Insert the point into TMP_SCREENS
                            batch.append((pk, x, y, z, self.target_srid))

        # Execute the batch insert
        self.database.execute_batch(
            """
            INSERT INTO TMP_SCREENS(
                pk,
                the_geom
            ) VALUES (
                ?,
                ST_SetSRID(
                    ST_MakePoint(?, ?, ?), ?)
                )
            """,
            batch,
        )

        logger.info("Finally, creating RECEIVERS table...")
        self.database.execute(
            f"""
            CREATE TABLE {config.receivers_table_name}(
                pk INT NOT NULL AUTO_INCREMENT,
                the_geom GEOMETRY,
                level integer,
                pk_building integer
            )
            """
        )

        self.database.execute(
            f"""
            INSERT INTO {config.receivers_table_name} (
                the_geom,
                level,
                pk_building
            ) SELECT
                ST_SetSRID(the_geom, {self.target_srid}),
                level,
                pk_building
            FROM TMP_SCREENS;
            """
        )
        self.database.execute(
            SQLBuilder.create_spatial_index(config.receivers_table_name)
        )

        if config.sources_table_name:
            logger.info(f"Deleting receivers near {config.sources_table_name}")
            self.database.execute(
                f"""
                DELETE FROM {config.receivers_table_name} g
                WHERE EXISTS (
                    SELECT 1
                    FROM {config.sources_table_name} r
                    WHERE ST_EXPAND(g.the_geom, 1, 1) && r.the_geom
                    AND ST_DISTANCE(g.the_geom, r.the_geom) < 1
                    LIMIT 1
                )
                """
            )

        return config.receivers_table_name
