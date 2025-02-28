from pathlib import Path
from sqlalchemy import ClauseElement, Column, MetaData, String, Table, create_engine, func, select, text
from typing import Optional, Dict, Any
from contextlib import contextmanager
from .java_bridge import JavaBridge

class NoiseDatabase:
    """Manages H2GIS database connections and operations for NoiseModelling."""

    def __init__(self, db_file: str = "noise_calc"):
        self.db_file = db_file
        self.java_bridge = JavaBridge.get_instance()
        self.connection = self._init_java_connection()
        self.metadata = MetaData()
    
    def _init_java_connection(self):
        """Initialize Java/H2GIS connection for spatial functions."""  
        
        db_path = Path(self.db_file).absolute()
        jdbc_url = f"jdbc:h2:{db_path};AUTO_SERVER=TRUE"
        
        props = self.java_bridge.Properties()
        props.setProperty("user", "sa")
        props.setProperty("password", "")

        # H2 database optimization settings
        props.setProperty("CACHE_SIZE", "65536")  # 64MB cache
        props.setProperty("LOCK_MODE", "0")       # Table-level locking
        props.setProperty("UNDO_LOG", "0")        # Disable undo log for batch operations
        props.setProperty("LOCK_TIMEOUT", "20000") # 20 second lock timeout
        
        # Create and initialize H2GIS connection
        conn = self.java_bridge.DriverManager.getConnection(jdbc_url, props)
        wrapped_conn = self.java_bridge.ConnectionWrapper(conn)
        
        # Important: Initialize H2GIS spatial functions AND metadata tables
        self.java_bridge.H2GISFunctions.load(conn)

        # Use SQL to ensure complete H2GIS initialization
        wrapped_conn.createStatement().execute("""
            CREATE ALIAS IF NOT EXISTS H2GIS_SPATIAL FOR "org.h2gis.functions.factory.H2GISFunctions.load";
            CALL H2GIS_SPATIAL();
        """)

        return wrapped_conn
    def _extract_srid(self, crs: str | None) -> int:
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
            if 'opengis.net/def/crs/EPSG' in crs:
                return int(crs.split('/')[-1])
        return int(crs)

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
                self.connection, 
                table_location
            )
            
            return pk_field_index > 0, pk_index > 0
            
        finally:
            statement.close()

    def add_primary_key(self, table_name: str) -> None:
        """Add primary key to table using SQLAlchemy."""
        statements = [
            text(f"ALTER TABLE {table_name} ALTER COLUMN PK INT NOT NULL"),
            text(f"ALTER TABLE {table_name} ADD PRIMARY KEY (PK)")
        ]
        for stmt in statements:
            self.execute(stmt)


    def fetch_one(self) -> tuple:
        """Fetch one row from the last executed query."""
        statement = self.connection.createStatement()
        try:
            result = statement.executeQuery(self._last_query)
            if result.next():
                meta = result.getMetaData()
                return tuple(
                    result.getObject(i + 1)
                    for i in range(meta.getColumnCount())
                )
            return None
        finally:
            statement.close()

    def execute(self, sql: str | ClauseElement, is_query: bool = False) -> None:
        """Execute SQL statement.
        
        Args:
            sql: SQL statement (string or SQLAlchemy clause)
            is_query: True if the SQL statement is a query
        """
        # Convert SQLAlchemy statement to string if needed
        if isinstance(sql, ClauseElement):
            sql = str(sql.compile(compile_kwargs={"literal_binds": True}))
        
        self._last_query = sql
        statement = self.connection.createStatement()
        try:
            if is_query:
                self._last_result = statement.executeQuery(sql)
            else:
                statement.execute(sql)
        finally:
            statement.close()
    
    def execute_batch(self, sql: str, values: list[tuple]) -> None:
        """Execute batch insert with prepared statement.
        
        Args:
            sql (str): SQL statement with parameter placeholders
            values (list[tuple]): List of value tuples to insert
        """
        statement = self.connection.prepareStatement(sql)
        try:
            for row in values:
                for i, value in enumerate(row):
                    statement.setObject(i + 1, value)
                statement.addBatch()
            statement.executeBatch()
        finally:
            statement.close()

    def query(self, sql: str) -> list[tuple]:
        """Execute SQL query and return all results.
        
        Args:
            sql (str): SQL query to execute
        
        Returns:
            list[tuple]: List of result rows
        """
        statement = self.connection.createStatement()
        try:
            result = statement.executeQuery(sql)
            meta = result.getMetaData()
            col_count = meta.getColumnCount()
            rows = []
            while result.next():
                rows.append(tuple(
                    result.getObject(i + 1)
                    for i in range(col_count)
                ))
            return rows
        finally:
            statement.close()

    def import_shapefile(self, file_path: str, table_name: str):
        """Import shapefile into database."""
        self.execute(f"""
            DROP TABLE IF EXISTS {table_name};
            CALL SHPREAD('{file_path}', '{table_name}');
        """)
    
    def import_geojson(self, file_path: str, table_name: str, crs: str | int = 4326) -> None:
        """Import GeoJSON file into database with proper spatial indexing and SRID handling.
        
        Args:
            file_path (str): Path to the GeoJSON file
            table_name (str): Name of the table to create
            srid (int, optional): Spatial reference identifier. Defaults to 4326 (WGS84).
        """
        
        # Get required Java classes through JavaBridge
        EmptyProgressVisitor = self.java_bridge.EmptyProgressVisitor
        TableLocation = self.java_bridge.TableLocation
        
        
        # Convert table name to uppercase to match Groovy behavior
        table_name = table_name.upper()
        
        # Drop table if exists
        self.drop_table(table_name)
        
        # Create Java File object from path
        file_obj = self.java_bridge.File(str(Path(file_path).absolute()))
        
        # Import GeoJSON using H2GIS driver
        driver = self.java_bridge.GeoJsonDriverFunction()

        # # Ensure spatial metadata tables exist
        self.execute("CREATE ALIAS IF NOT EXISTS H2GIS_SPATIAL FOR \"org.h2gis.functions.factory.H2GISFunctions.load\";")
        self.execute("CALL H2GIS_SPATIAL();")

        driver.importFile(self.connection, table_name, file_obj, EmptyProgressVisitor())
        
        table_location = TableLocation.parse(table_name, self.java_bridge.DBUtils.getDBType(self.connection))
        # Get spatial field names
        spatial_fields = [
            str(field) for field in self.java_bridge.GeometryTableUtilities.getGeometryColumnNames(
                self.connection, 
                table_location
            )
        ]
        if not spatial_fields:
            # logger.warn("The table " + tableName + " does not contain a geometry field.")
            print("Warning")
            return
        
        # Create spatial index
        self.execute(
            f"CREATE SPATIAL INDEX IF NOT EXISTS {table_name}_INDEX ON {table_name}(the_geom)"
        )
        
        # Check and set SRID
        table_srid = self.java_bridge.GeometryTableUtilities.getSRID(
            self.connection, TableLocation.parse(table_name)
        )

        srid = self._extract_srid(crs)
        
        if table_srid == 0 and spatial_fields and srid:
            # Update SRID if not set
            self.execute(
                f"SELECT UpdateGeometrySRID('{table_name}', '{spatial_fields[0]}', {srid})"
            )
        
        # Check for PK column and set primary key if needed
        has_pk_column, has_pk_constraint = self.check_pk_column(table_name)
        
        if has_pk_column and not has_pk_constraint:
            self.add_primary_key(table_name)

    def cleanup(self):
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

    def clear_database(self) -> None:
        """Remove the database file completely."""
        self.cleanup()
        db_file = Path(self.db_file)
        for ext in ['.mv.db', '.trace.db']:
            file = db_file.with_suffix(ext)
            if file.exists():
                file.unlink()