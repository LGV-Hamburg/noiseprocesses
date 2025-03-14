import json
import os
import re
import tempfile
from contextlib import contextmanager
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, Generator

from sqlalchemy import ClauseElement, MetaData, text

from noiseprocesses.core.java_bridge import JavaBridge

logger = getLogger(__name__)


class SQLBuilder:
    @staticmethod
    def drop_table(table_name: str) -> str:
        safe_name = f'"{table_name.replace('"', '""')}"'
        return f"DROP TABLE IF EXISTS {safe_name}"

    @staticmethod
    def create_spatial_index(table_name: str) -> str:
        safe_name = f'"{table_name.replace('"', '""')}"'
        return f"CREATE SPATIAL INDEX ON {safe_name}(the_geom)"

    # using CTAS here, named parameters are not supported
    @staticmethod
    def create_grid_table(
        table_name: str, fence_geom: str, height: float, srid: int, delta: float
    ) -> str:
        return f"""
            CREATE TABLE {table_name} AS 
            SELECT 
                ST_SETSRID(
                    ST_UPDATEZ(THE_GEOM, {height}), 
                    {srid}
                ) AS THE_GEOM,
                ID_COL,
                ID_ROW 
            FROM ST_MakeGridPoints(
                ST_GeomFromText('{str(fence_geom)}'),
                {delta},
                {delta}
            )
        """

    @staticmethod
    def create_table(table_name: str, columns: list[tuple[str, str]]) -> str:
        """
        Create safe CREATE TABLE statement.

        Args:
            table_name: Table name
            columns: List of (name, type) tuples
        """
        safe_name = SQLBuilder.quote_identifier(table_name)
        safe_columns = [
            f"{SQLBuilder.quote_identifier(name)} {type_}" for name, type_ in columns
        ]
        return f"CREATE TABLE {safe_name} ({', '.join(safe_columns)})"

    @staticmethod
    def quote_identifier(identifier: str) -> str:
        """Safely quote table/column identifiers."""
        if not identifier:
            raise ValueError("Empty identifier")
        return f'"{identifier.replace('"', '""')}"'

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate table/column name."""
        return bool(re.match(r"^[A-Za-z][A-Za-z0-9_]*$", identifier))


class NoiseDatabase:
    """Manages H2GIS database connections and operations for NoiseModelling."""

    def __init__(self, db_file: str, in_memory: bool = False):
        self.db_file = db_file
        self.in_memory = in_memory
        self._last_query = None  # Add this line to track last query
        self.java_bridge = JavaBridge.get_instance()
        self.connection = self._init_java_connection()
        self.metadata = MetaData()

        # Initialize H2GIS spatial extension
        self._init_spatial_extension()

    def _init_java_connection(self):
        """Initialize Java/H2GIS connection for spatial functions."""

        db_path = Path(self.db_file).absolute()

        jdbc_url = f"jdbc:h2:{db_path};AUTO_SERVER=TRUE"
        if self.in_memory:
            jdbc_url = f"jdbc:h2:mem:{db_path};DB_CLOSE_DELAY=-1"  # DB_CLOSE_DELAY=-1" creates a potential memory leak!

        props = self.java_bridge.Properties()
        props.setProperty("user", "sa")
        props.setProperty("password", "")

        # H2 database optimization settings
        props.setProperty("CACHE_SIZE", "65536")  # 64MB cache
        props.setProperty("LOCK_MODE", "0")  # Table-level locking
        props.setProperty("UNDO_LOG", "0")  # Disable undo log for batch operations
        props.setProperty("LOCK_TIMEOUT", "20000")  # 20 second lock timeout
        props.setProperty("MVCC", "TRUE")  # Better concurrency
        props.setProperty("DB_CLOSE_DELAY", "-1")  # Keep database open
        props.setProperty("WR", "0")  # Write changes immediately

        # Create and initialize H2GIS connection
        conn = self.java_bridge.DriverManager.getConnection(jdbc_url, props)
        wrapped_conn = self.java_bridge.ConnectionWrapper(conn)

        return wrapped_conn

    def _init_spatial_extension(self):
        # Important: Initialize H2GIS spatial functions
        self.java_bridge.H2GISFunctions.load(self.connection)
        # or use this directly
        # self.execute(
        #     'CREATE ALIAS IF NOT EXISTS H2GIS_SPATIAL FOR "org.h2gis.functions.factory.H2GISFunctions.load";'
        # )
        # self.execute("CALL H2GIS_SPATIAL();")

    @contextmanager
    def _get_prepared_statement(self, sql: str):
        """Context manager for prepared statements."""
        stmt = self.connection.prepareStatement(sql)
        try:
            yield stmt
        finally:
            stmt.close()

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Transaction context manager using JDBC."""
        auto_commit = self.connection.getAutoCommit()
        self.connection.setAutoCommit(False)
        try:
            yield
            self.connection.commit()
        except:
            self.connection.rollback()
            raise
        finally:
            self.connection.setAutoCommit(auto_commit)

    def _bind_parameters(self, stmt, params: dict) -> None:
        """Bind parameters to prepared statement.

        Args:
            stmt: JDBC PreparedStatement
            params: Dictionary of parameter names and values
        """
        if not params:
            return

        # Convert named parameters to positional
        sql = stmt.toString()
        param_order = []

        # Extract parameter names in order
        for key in params.keys():
            param_name = f":{key}"
            if param_name in sql:
                param_order.append(key)

        # Bind parameters in correct order
        for i, param_name in enumerate(param_order, start=1):
            value = params[param_name]

            # Handle different Java types
            if isinstance(value, (int, bool)):
                stmt.setInt(i, value)
            elif isinstance(value, float):
                stmt.setDouble(i, value)
            elif value is None:
                stmt.setNull(i, self.java_bridge.Types.NULL)
            else:
                stmt.setObject(i, value)

        # Store query for fetch_one method
        self._last_query = sql

    def _extract_srid(self, crs: str | int | None) -> int:
        """Extract SRID from CRS string.

        Args:
            crs (str | None): CRS string in URL or EPSG code format
                Examples:
                    - "http://www.opengis.net/def/crs/EPSG/0/3857"
                    - 3857

        Returns:
            int: SRID value, defaults to 4326 if crs is None
        """
        if crs is None:
            return 4326

        if isinstance(crs, str):
            if "opengis.net/def/crs/EPSG" in crs:
                return int(crs.split("/")[-1])
        return int(crs)

    def create_spatial_index(self, table_name) -> None:
        """Create spatial index for a table."""
        self.execute(f"""
            CREATE SPATIAL INDEX IF NOT EXISTS {table_name}_INDEX
            ON {table_name}(THE_GEOM);
        """)

    def optimize_table(self, table_name: str) -> None:
        """Optimize table with proper indexes and clustering."""
        # Create spatial index if geometry exists
        self.execute(f"""
            -- Cluster table by spatial index
            CLUSTER {table_name} USING {table_name}_GEOM_IDX;

            -- Analyze table for query optimization
            ANALYZE {table_name};
        """)

    def check_pk_column(self, table_name: str) -> tuple[bool, bool]:
        """Check if table has PK column and if it's a primary key.

        Args:
            table_name (str): Name of the table to check

        Returns:
            tuple[bool, bool]: (has_pk_column, has_pk_constraint)
        """
        statement = self.connection.createStatement()
        try:
            # Check for PK column existence
            result = statement.executeQuery(f"SELECT * FROM {table_name}")
            meta = result.getMetaData()
            pk_field_index = self.java_bridge.JDBCUtilities.getFieldIndex(meta, "PK")

            # Check for primary key constraint
            table_location = self.java_bridge.TableLocation.parse(table_name)
            pk_index = self.java_bridge.JDBCUtilities.getIntegerPrimaryKey(
                self.connection, table_location
            )

            return pk_field_index > 0, pk_index > 0

        finally:
            statement.close()

    def add_primary_key(self, table_name: str) -> None:
        """Add primary key to table using SQLAlchemy."""
        statements = [
            text(f"ALTER TABLE {table_name} ALTER COLUMN PK INT NOT NULL"),
            text(f"ALTER TABLE {table_name} ADD PRIMARY KEY (PK)"),
        ]
        for stmt in statements:
            self.execute(stmt)

    def fetch_one(self) -> tuple | None:
        """Fetch one row from the last executed query."""
        statement = self.connection.createStatement()
        try:
            result = statement.executeQuery(self._last_query)
            if result.next():
                meta = result.getMetaData()
                return tuple(
                    result.getObject(i + 1) for i in range(meta.getColumnCount())
                )
            return None
        finally:
            statement.close()

    def query_scalar(self, sql: str, params: dict | None = None) -> Any:
        """Get single value with consistent handling."""
        with self._get_prepared_statement(sql) as stmt:
            if params:
                self._bind_parameters(stmt, params)
            result = stmt.executeQuery()

            if result.next():
                return result.getObject(1)  # Get first column directly
            return None

    def execute(self, sql: str | ClauseElement, params: dict | None = None) -> None:
        """Execute SQL with consistent parameter handling."""
        sql_str = self._get_sql_string(sql)

        with self._get_prepared_statement(sql_str) as stmt:
            if params:
                self._bind_parameters(stmt, params)
            stmt.execute()

    def _get_sql_string(self, sql: str | ClauseElement) -> str:
        """Convert any SQL input to string."""
        if isinstance(sql, ClauseElement):
            return str(sql.compile(compile_kwargs={"literal_binds": True}))
        return sql

    def execute_batch(self, sql: str, params: list[tuple]) -> None:
        """Execute batch insert with prepared statement.

        Args:
            sql (str): SQL statement with parameter placeholders
            values (list[tuple]): List of value tuples to insert
        """
        statement = self.connection.prepareStatement(sql)
        try:
            for row in params:
                for i, value in enumerate(row):
                    statement.setObject(i + 1, value)
                statement.addBatch()
            statement.executeBatch()
        finally:
            statement.close()

    def _result_set_to_tuples(self, result_set) -> list[tuple]:
        """Convert JDBC ResultSet to list of tuples."""
        meta = result_set.getMetaData()
        col_count = meta.getColumnCount()
        rows = []
        while result_set.next():
            rows.append(tuple(result_set.getObject(i + 1) for i in range(col_count)))
        return rows

    def query(self, sql: str, params: dict | None = None) -> list[tuple]:
        """Execute query with consistent resource management."""
        with self._get_prepared_statement(sql) as stmt:
            if params:
                self._bind_parameters(stmt, params)
            result = stmt.executeQuery()
            return self._result_set_to_tuples(result)

    def import_shapefile(self, file_path: str, table_name: str):
        """Import shapefile into database."""
        self.execute(f"""
            DROP TABLE IF EXISTS {table_name};
            CALL SHPREAD('{file_path}', '{table_name}');
        """)

    def import_geojson(
        self, source: str | Dict[str, Any], table_name: str, crs: str | int = 4326
    ) -> None:
        """Import GeoJSON into database with proper spatial indexing and SRID handling.

        Args:
            source: Path to GeoJSON file or GeoJSON dictionary
            table_name: Name of the table to create
            crs: Spatial reference identifier, defaults to 4326 (WGS84)
        """
        # Initialize H2GIS if needed
        self._init_spatial_extension()

        # Convert table name to uppercase
        table_name = table_name.upper()

        # Drop existing table
        self.drop_table(table_name)

        # Get Java bridge classes
        EmptyProgressVisitor = self.java_bridge.EmptyProgressVisitor
        driver = self.java_bridge.GeoJsonDriverFunction()

        # Handle different input types
        if isinstance(source, str) and os.path.exists(source):
            # File path input
            file_obj = self.java_bridge.File(str(Path(source).absolute()))
            driver.importFile(
                self.connection, table_name, file_obj, EmptyProgressVisitor()
            )
        else:
            # Dictionary input or string path that doesn't exist
            # (assume it's GeoJSON content)
            if isinstance(source, dict):
                json_str = json.dumps(source)
            else:  # Assume it's already a JSON string
                json_str = source

            # Create a temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".geojson", delete=False
            ) as temp_file:
                temp_file.write(json_str.encode("utf-8"))
                temp_path = temp_file.name
                logger.debug(f"Created temporary file: {temp_path}")

            try:
                # Import from temp file
                file_obj = self.java_bridge.File(temp_path)
                driver.importFile(
                    self.connection, table_name, file_obj, EmptyProgressVisitor()
                )
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        # Process imported table
        self._process_imported_table(table_name, crs)

    def _process_imported_table(self, table_name: str, crs: str | int) -> None:
        """Process an imported table with indexing and SRID handling."""
        TableLocation = self.java_bridge.TableLocation
        table_location = TableLocation.parse(
            table_name, self.java_bridge.DBUtils.getDBType(self.connection)
        )

        # Get spatial fields
        spatial_fields = [
            str(field)
            for field in self.java_bridge.GeometryTableUtilities.getGeometryColumnNames(
                self.connection, table_location
            )
        ]
        if not spatial_fields:
            print("Warning: Table does not contain geometry field")
            return

        # Create spatial index
        self.create_spatial_index(table_name)

        # Handle SRID
        table_srid = self.java_bridge.GeometryTableUtilities.getSRID(
            self.connection, TableLocation.parse(table_name)
        )
        srid = self._extract_srid(crs)

        if table_srid == 0 and spatial_fields and srid:
            self.execute(
                f"SELECT UpdateGeometrySRID('{table_name}', '{spatial_fields[0]}', {srid})"
            )

        # Handle primary key
        has_pk_column, has_pk_constraint = self.check_pk_column(table_name)
        if has_pk_column and not has_pk_constraint:
            self.add_primary_key(table_name)

    def import_raster(
        self, file_path, output_table="DEM", srid=4326, fence=None, downscale=1
    ):
        """
        Import a raster file into H2GIS database.

        Args:
            file_path: Path to the raster file
            output_table: Name of the output table
            srid: Default SRID to use if not specified in the file
            fence: WKT string of a polygon to limit the import area
            downscale: Factor to downscale the raster (1 = no downscale)

        Returns:
            String with information about the import
        """
        # Validate file existence
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Create statement
        stmt = self.connection.createStatement()

        # Drop table if exists
        stmt.execute(f"DROP TABLE IF EXISTS {output_table}")

        # Get file extension and choose appropriate driver
        ext = os.path.splitext(file_path)[1].lower()[1:]

        if ext == "asc":
            return self._import_asc(
                file_path, output_table, srid, fence, downscale, stmt
            )
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def _import_asc(self, file_path, output_table, srid, fence, downscale, stmt):
        """
        Import an ASC file using AscReaderDriver
        """
        logger.info(f"Importing ASC file: {file_path}")

        # Create ASC driver
        asc_driver = self.java_bridge.AscReaderDriver()
        asc_driver.setAs3DPoint(True)

        # Check for PRJ file to determine SRID
        file_prefix = os.path.splitext(file_path)[0]
        prj_file = f"{file_prefix}.prj"

        if os.path.exists(prj_file):
            logger.info(f"Found PRJ file: {prj_file}")
            try:
                detected_srid = self.java_bridge.PRJUtil.getSRID(
                    self.java_bridge.File(prj_file)
                )
                if detected_srid != 0:
                    srid = detected_srid
            except Exception as e:
                logger.warning(
                    f"Error reading PRJ file: {e}. Using default SRID: {srid}"
                )

        # Apply fence if provided
        if fence:
            wkt_reader = self.java_bridge.WKTReader()
            wkt_writer = self.java_bridge.WKTWriter()

            fence_geom = wkt_reader.read(fence)
            logger.info(f"Got fence: {wkt_writer.write(fence_geom)}")

            # Transform fence to match the DEM coordinate system
            fence_transform = self.java_bridge.ST_Transform.ST_Transform(
                self.connection,
                self.java_bridge.ST_SetSRID.setSRID(fence_geom, 4326),
                srid,
            )

            # Get envelope from transformed geometry
            envelope = fence_transform.getEnvelopeInternal()
            asc_driver.setExtractEnvelope(envelope)
            logger.info(
                f"Fence coordinate transformed: {wkt_writer.write(fence_transform)}"
            )

        # Apply downscaling if requested
        if downscale > 1:
            asc_driver.setDownScale(downscale)

        # Import the ASC file
        progress_visitor = self.java_bridge.RootProgressVisitor(1, True, 1)
        asc_driver.read(
            self.connection,
            self.java_bridge.File(file_path),
            progress_visitor,
            output_table,
            srid,
        )

        # Create spatial index
        logger.info(f"Creating spatial index on {output_table}")
        stmt.execute(f"CREATE SPATIAL INDEX ON {output_table}(the_geom)")

        return f"Table {output_table} has been created with SRID {srid}"

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def drop_table(self, table_name: str) -> None:
        """Drop a table if it exists.

        Args:
            table_name (str): Name of the table to drop
        """
        self.execute(f"DROP TABLE IF EXISTS {table_name}")

    def drop_all_tables(self) -> None:
        """Drop all tables in the database."""
        # Get list of tables first
        tables = self.query("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA='PUBLIC'
        """)

        # Drop each table
        for (table_name,) in tables:
            self.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

    def clear_database(self, path: str | None = None) -> None:
        """Remove the database file completely."""
        self.disconnect()
        db_file = path or self.db_file
        db_path = Path(db_file)

        for ext in [".mv.db", ".trace.db"]:
            file = db_path.with_suffix(ext)
            if file.exists():
                file.unlink()

    def export_data(self, table_to_export: str) -> str:
        logger.info(f"Exporting {table_to_export} to a temporary GeoJSON file")

        table_to_export = table_to_export.upper()
        fields = self.java_bridge.JDBCUtilities.getColumnNames(
            self.connection, table_to_export
        )
        if not fields:
            raise Exception("The table is empty and cannot be exported.")

        # Create a temporary file for the GeoJSON export
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as temp_file:
            export_path = temp_file.name

        export_file = self.java_bridge.File(export_path)
        progress_visitor = self.java_bridge.EmptyProgressVisitor()
        driver = self.java_bridge.GeoJsonDriverFunction()

        driver.exportTable(
            self.connection, table_to_export, export_file, True, progress_visitor
        )

        return export_path
