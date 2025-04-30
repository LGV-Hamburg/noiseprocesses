import logging

from pathlib import Path

from noiseprocesses.utils import srid
from noiseprocesses.core.database import NoiseDatabase, SQLBuilder
from noiseprocesses.models.grid_config import DelaunayGridConfig, RegularGridConfig
from noiseprocesses.core.java_bridge import JavaBridge


logger = logging.getLogger(__name__)


class DelaunayGridGenerator:
    """Generates a Delaunay triangulation grid of receivers"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0

    def generate_receivers(self, config: DelaunayGridConfig) -> str:
        """
        Generate Delaunay grid of receivers

        Args:
            config: Configuration for grid generation

        Returns:
            str: Name of created receivers table
        """
        logger.info("Starting Delaunay grid generation")

        # Get SRID from input tables
        self.target_srid = srid.get_srid(
            self.database,
            self.java_bridge,
            config
        )

        # Drop existing tables
        self.database.execute(
            SQLBuilder.drop_table(config.output_table)
        )
        self.database.execute("DROP TABLE IF EXISTS TRIANGLES")

        # Initialize NoiseModelling triangulation
        logger.info("Initializing triangulation")
        triangle_map = self.java_bridge.TriangleNoiseMap(
            config.buildings_table,
            config.sources_table if config.sources_table else ""
        )

        # Configure triangulation parameters
        self._configure_triangulation(triangle_map, config)

        # Process grid cells
        pk = self.java_bridge.AtomicInteger(0)
        grid_dim = triangle_map.getGridDim()
        total_cells = grid_dim * grid_dim

        try:
            # could possibly be parallelized
            for i in range(grid_dim):
                for j in range(grid_dim):
                    logger.info(
                        f"Computing cell {i * grid_dim + j + 1} of {total_cells}"
                    )
                    triangle_map.generateReceivers(
                        self.database.connection,
                        i, j,
                        config.output_table,
                        "TRIANGLES",
                        pk
                    )

        except Exception as e:
            logger.error(
                "Error during triangulation. Use error_dump_folder parameter "
                "to save input geometries for debugging."
            )
            if config.error_dump_folder:
                self._handle_error(config, triangle_map, e)
            raise

        # Create spatial index
        logger.info(f"Creating spatial index on {config.output_table}")
        self.database.execute(
            f"CREATE SPATIAL INDEX ON {config.output_table}(the_geom)"
        )

        # Log completion
        receiver_count = self.database.query_scalar(
            f"SELECT COUNT(*) FROM {config.output_table}"
        )
        logger.info(f"Created {receiver_count} receivers")

        return config.output_table

    def _configure_triangulation(
            self, triangle_map, config: DelaunayGridConfig
    ) -> None:
        """Configure triangulation parameters"""
        # Set basic parameters
        triangle_map.setMaximumArea(config.max_area)
        triangle_map.setRoadWidth(config.road_width)
        triangle_map.setReceiverHeight(config.height)
        triangle_map.setIsoSurfaceInBuildings(config.iso_surface_in_buildings)
        triangle_map.setMaximumPropagationDistance(config.max_cell_dist)

        # Configure fence if provided
        if config.fence_geometry:
            fence = self.java_bridge.ST_Transform.transform(
                self.database.connection,
                self.java_bridge.ST_SetSRID.setSRID(
                    str(config.fence_geometry),
                    4326
                ),
                self.target_srid
            )
            triangle_map.setMainEnvelope(fence.getEnvelopeInternal())

        # Set debug folder if provided
        if config.error_dump_folder:
            triangle_map.setExceptionDumpFolder(str(Path(config.error_dump_folder)))

        triangle_map.initialize(
            self.database.connection,
            self.java_bridge.EmptyProgressVisitor()
        )

    def _process_grid_cell(
        self, 
        triangle_map, 
        config: DelaunayGridConfig,
        i: int, 
        j: int, 
        pk: int
    ) -> int:
        """Process a single grid cell"""
        try:
            return triangle_map.generateReceivers(
                self.database.connection,
                i, j,
                config.output_table,
                "TRIANGLES",
                pk
            )
        except Exception as e:
            logger.error(f"Error processing cell ({i},{j}): {str(e)}")
            raise

    def _handle_error(
        self, 
        config: DelaunayGridConfig,
        triangle_map,
        error: Exception
    ) -> None:
        """Handle triangulation error with debug information"""
        if hasattr(triangle_map, "getErrorDumpFolder"):
            dump_folder = triangle_map.getErrorDumpFolder()
            logger.info(f"Error debug information dumped to: {dump_folder}")

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

        self.target_srid = srid.get_srid(
            self.database,
            self.java_bridge,
            config
        )

        fence_envelop = self._get_fence_envelop(config, self.target_srid)

        # Create receivers table
        self._create_receivers_table(config.output_table, fence_envelop, config)

        # Post-process receivers
        self._process_receivers(config, fence_envelop)

        if config.create_triangles:
            self._create_triangles(config.output_table, self.target_srid)

        return config.output_table

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
        self.database.execute(SQLBuilder.drop_table(table_name))
        self.database.execute(SQLBuilder.create_grid_table(
            table_name,
            fence_geom,
            config.height,
            self.target_srid,
            config.delta
        ))
        self.database.execute(f"""
            ALTER TABLE {table_name} ADD COLUMN PK SERIAL PRIMARY KEY;
        """
        )

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
        self.database.execute(SQLBuilder.drop_table("TRIANGLES"))
        self.database.execute(f"""
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
