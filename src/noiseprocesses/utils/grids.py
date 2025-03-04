import logging

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import RegularGridConfig
from noiseprocesses.core.java_bridge import JavaBridge
logger = logging.getLogger(__name__)


class RegularGridGenerator:
    """Generates a regular grid of receivers"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0

    def generate_receivers(self, config: RegularGridConfig) -> str:
        """
        Generate regular grid of receivers

        Args:
            config: Configuration for grid generation

        Returns:
            str: Name of created receivers table
        """
        logger.info("Starting regular grid generation")

        self.target_srid = self._get_srid(config)

        fence_envelop = self._get_fence_envelop(config, self.target_srid)

        # Create receivers table
        self._create_receivers_table(config.output_table, fence_envelop, config)

        # Post-process receivers
        self._process_receivers(config, fence_envelop)

        if config.create_triangles:
            self._create_triangles(config.output_table, self.target_srid)

        return config.output_table

    def _get_srid(self, config: RegularGridConfig) -> int:
        """Determine SRID from input tables"""

        srid = 0

        TableLocation = self.database.java_bridge.TableLocation

        if self.target_srid == 0 and config.buildings_table:
            srid = self.java_bridge.GeometryTableUtilities.getSRID(
                self.database.connection, TableLocation.parse(config.buildings_table)
            )

        if self.target_srid == 0 and config.sources_table:
            srid = self.java_bridge.GeometryTableUtilities.getSRID(
                self.database.connection, TableLocation.parse(config.sources_table)
            )
        
        if self.target_srid == 0 and config.fence_table:
            srid = self.java_bridge.GeometryTableUtilities.getSRID(
                self.database.connection, TableLocation.parse(config.fence_table)
            )

        self.target_srid = srid

        if self.target_srid in (0, 3785, 4326):
            raise ValueError(f"Invalid SRID: {srid}. Please use a metric projection system.")

        return srid

    def _get_fence_strategies(self, config: RegularGridConfig, srid: int) -> dict:
        """Define fence geometry calculation strategies"""
        return {
            # WKT fence has highest priority, transform wkt to target SRID
            "fence_geometry": self.java_bridge.ST_Transform.ST_Transform(
                self.database.connection,
                self.java_bridge.ST_SetSRID.setSRID(config.fence_geometry, 4326),
                srid
            ) if config.fence_geometry else None,
            
            # Fence table has second priority
            "fence_table": self.java_bridge.GeometryTableUtilities.getEnvelope(
                self.database.connection,
                self.java_bridge.TableLocation.parse(config.fence_table), "THE_GEOM"
            ) if config.fence_table else None,
            
            # Buildings table has lowest priority
            "buildings": self.java_bridge.GeometryTableUtilities.getEnvelope(
                self.database.connection,
                self.java_bridge.TableLocation.parse(config.buildings_table), "THE_GEOM"
            ) if config.buildings_table.lower() else None
        }

    def _get_fence_envelop(self, config: RegularGridConfig, srid: int):
        """Get fence envelope using strategy pattern"""
        strategies = self._get_fence_strategies(config, srid)
        
        for strategy_name, strategy_func in strategies.items():
            try:
                if result := strategy_func:
                    logger.debug(f"Using {strategy_name} strategy for fence geometry")
                    return result
            except Exception as e:
                logger.warning(
                    f"Strategy {strategy_name} failed: {str(e)}, trying next"
                )
        
        raise ValueError("No valid fence geometry source available")

    def _create_receivers_table(
        self, table_name: str, fence_geom, config: RegularGridConfig
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
                ST_SETSRID(ST_UPDATEZ(THE_GEOM, {config.height}), {self.target_srid}) AS THE_GEOM,
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
        self,
        config: RegularGridConfig,
        fence_envelop
    ) -> None:
        """Apply filters and process receivers"""
        # Delete receivers outside fence
        if config.fence_geometry:
            self.database.execute(
                f"""
                DELETE FROM {config.output_table}
                WHERE NOT ST_Intersects(THE_GEOM, :geom)
            """,
                {"geom": fence_envelop},
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
