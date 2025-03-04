import logging

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import RegularGridConfig
from noiseprocesses.core.java_bridge import JavaBridge
logger = logging.getLogger(__name__)


class RegularGridGenerator:
    """Generates a regular grid of receivers"""

    def __init__(self, database: NoiseDatabase):
        self.database = database

    def generate_receivers(self, config: RegularGridConfig) -> str:
        """
        Generate regular grid of receivers

        Args:
            config: Configuration for grid generation

        Returns:
            str: Name of created receivers table
        """
        logger.info("Starting regular grid generation")

        TableLocation = self.database.java_bridge.TableLocation

        # Validate inputs and get SRID
        srid = self.database.java_bridge.GeometryTableUtilities.getSRID(
            self.database.connection, TableLocation.parse(config.buildings_table)
        )
        fence_geom = self._get_fence_geometry(config, srid)

        # Create receivers table
        self._create_receivers_table(config.output_table, fence_geom, config)

        # Post-process receivers
        self._process_receivers(config, fence_geom)

        if config.create_triangles:
            self._create_triangles(config.output_table, srid)

        return config.output_table

    def _get_srid(self, config: RegularGridConfig) -> int:
        """Determine SRID from input tables"""
        srid = config.srid
        if srid == 0 and config.buildings_table:
            srid = self.database.get_srid(config.buildings_table)
        if srid == 0 and config.sources_table:
            srid = self.database.get_srid(config.sources_table)
        if srid in (0, 3785, 4326):
            raise ValueError("Invalid SRID. Please use a metric projection system.")
        return srid

    def _get_fence_geometry(self, config: RegularGridConfig, srid: int) -> "Geometry":
        """Get or create fence geometry"""
        if config.fence_geometry:
            return self.database.transform_geometry(config.fence_geom, 4326, srid)
        elif config.fence_table:
            return self.database.get_envelope(config.fence_table)
        elif config.buildings_table:
            return self.database.get_envelope(config.buildings_table)
        else:
            raise ValueError("No fence geometry or reference table provided")

    def _create_receivers_table(
        self, table_name: str, fence_geom: "Geometry", config: RegularGridConfig
    ) -> None:
        """Create initial receivers grid table"""
        self.database.execute(f"""
            DROP TABLE IF EXISTS {table_name};
            CREATE TABLE {table_name} (
                THE_GEOM GEOMETRY,
                ID_COL INTEGER,
                ID_ROW INTEGER
            ) AS 
            SELECT 
                ST_SETSRID(ST_UPDATEZ(THE_GEOM, {config.height}), {config.srid}) AS THE_GEOM,
                ID_COL,
                ID_ROW 
            FROM ST_MakeGridPoints(
                ST_GeomFromText('{fence_geom}'),
                {config.delta},
                {config.delta}
            );
            ALTER TABLE {table_name} ADD COLUMN PK SERIAL PRIMARY KEY;
        """)

        # Create spatial index
        self.database.execute(f"CREATE SPATIAL INDEX ON {table_name}(the_geom)")

    def _process_receivers(
        self, config: RegularGridConfig, fence_geom: "Geometry"
    ) -> None:
        """Apply filters and process receivers"""
        # Delete receivers outside fence
        if config.fence_geom:
            self.database.execute(
                f"""
                DELETE FROM {config.output_table}
                WHERE NOT ST_Intersects(THE_GEOM, :geom)
            """,
                {"geom": fence_geom},
            )

        # Delete receivers inside buildings
        if config.buildings_table:
            self.database.execute(f"""
                DELETE FROM {config.output_table} g 
                WHERE EXISTS (
                    SELECT 1 FROM {config.buildings_table} b 
                    WHERE ST_Z(g.the_geom) < b.HEIGHT 
                    AND g.the_geom && b.the_geom 
                    AND ST_INTERSECTS(g.the_geom, b.the_geom) 
                    AND ST_distance(b.the_geom, g.the_geom) < 1 
                    LIMIT 1
                )
            """)

        # Delete receivers near sources
        if config.sources_table:
            self.database.execute(f"""
                DELETE FROM {config.output_table} g 
                WHERE EXISTS (
                    SELECT 1 FROM {config.sources_table} r 
                    WHERE st_expand(g.the_geom, 1) && r.the_geom 
                    AND st_distance(g.the_geom, r.the_geom) < 1 
                    LIMIT 1
                )
            """)

    def _create_triangles(self, receivers_table: str, srid: int) -> None:
        """Create triangles from receivers grid"""
        self.database.execute(f"""
            DROP TABLE IF EXISTS TRIANGLES;
            CREATE TABLE TRIANGLES(
                pk serial NOT NULL,
                the_geom geometry(POLYGON Z, {srid}),
                PK_1 integer not null,
                PK_2 integer not null,
                PK_3 integer not null,
                cell_id integer not null,
                PRIMARY KEY (PK)
            );
            
            -- Insert first set of triangles
            INSERT INTO TRIANGLES(THE_GEOM, PK_1, PK_2, PK_3, CELL_ID)
            SELECT 
                ST_ConvexHull(ST_UNION(A.THE_GEOM, ST_UNION(B.THE_GEOM, C.THE_GEOM))) THE_GEOM,
                A.PK PK_1, B.PK PK_2, C.PK PK_3, 0
            FROM {receivers_table} A, {receivers_table} B, {receivers_table} C
            WHERE A.ID_ROW = B.ID_ROW + 1 
            AND A.ID_COL = B.ID_COL
            AND A.ID_ROW = C.ID_ROW + 1 
            AND A.ID_COL = C.ID_COL + 1;
            
            -- Insert second set of triangles
            INSERT INTO TRIANGLES(THE_GEOM, PK_1, PK_2, PK_3, CELL_ID)
            SELECT 
                ST_ConvexHull(ST_UNION(A.THE_GEOM, ST_UNION(B.THE_GEOM, C.THE_GEOM))) THE_GEOM,
                A.PK PK_1, B.PK PK_2, C.PK PK_3, 0
            FROM {receivers_table} A, {receivers_table} B, {receivers_table} C
            WHERE A.ID_ROW = B.ID_ROW + 1 
            AND A.ID_COL = B.ID_COL + 1
            AND A.ID_ROW = C.ID_ROW 
            AND A.ID_COL = C.ID_COL + 1;
        """)
