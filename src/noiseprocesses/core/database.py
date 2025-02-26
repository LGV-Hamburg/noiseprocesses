from pathlib import Path
from sqlalchemy import ClauseElement, create_engine, text
from typing import Optional, Dict, Any
from contextlib import contextmanager
from .java_bridge import JavaBridge

class NoiseDatabase:
    """Manages H2GIS database connections and operations for NoiseModelling."""

    def __init__(self, db_file: str = "noise_calc"):
        self.db_file = db_file
        self.java_bridge = JavaBridge.get_instance()
        self.connection = self._init_java_connection()
    
    def _init_java_connection(self):
        """Initialize Java/H2GIS connection for spatial functions."""
        from jnius import autoclass
        
        DriverManager = autoclass('java.sql.DriverManager')
        H2GISFunctions = autoclass('org.h2gis.functions.factory.H2GISFunctions')
        Properties = autoclass('java.util.Properties')
        
        db_path = Path(self.db_file).absolute()
        jdbc_url = f"jdbc:h2:{db_path};AUTO_SERVER=TRUE"
        
        props = Properties()
        props.setProperty("user", "sa")
        props.setProperty("password", "")
        
        # Create and initialize H2GIS connection
        conn = DriverManager.getConnection(jdbc_url, props)
        H2GISFunctions.load(conn)
        return self.java_bridge.ConnectionWrapper(conn)
    
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
    
    def import_geojson(self, file_path: str, table_name: str):
        """Import GeoJSON file into database.
        
        Args:
            file_path (str): Path to the GeoJSON file
            table_name (str): Name of the table to create
        """
        from jnius import autoclass
        
        # Get required Java classes
        GeoJsonDriverFunction = autoclass('org.h2gis.functions.io.geojson.GeoJsonDriverFunction')
        EmptyProgressVisitor = autoclass('org.h2gis.api.EmptyProgressVisitor')
        File = autoclass('java.io.File')
        
        # Drop table if exists
        self.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create Java File object from path
        file_obj = File(str(Path(file_path).absolute()))
        
        # Import GeoJSON
        driver = GeoJsonDriverFunction()
        driver.importFile(self.connection, table_name, file_obj, EmptyProgressVisitor())

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