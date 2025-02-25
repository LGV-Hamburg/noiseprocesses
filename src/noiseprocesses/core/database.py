from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
from .java_bridge import JavaBridge

class NoiseDatabase:
    """Manages H2GIS database connections and operations for NoiseModelling."""
    
    def __init__(self, db_file: str = "noise_calc"):
        self.db_file = db_file
        self.connection = None
        self.java_bridge = JavaBridge.get_instance()
        self._init_db()
    
    def _init_db(self):
        """Initialize H2GIS database connection using JNI."""
        from jnius import autoclass
        
        # Get required Java classes
        DriverManager = autoclass('java.sql.DriverManager')
        H2GISFunctions = autoclass('org.h2gis.functions.factory.H2GISFunctions')
        Properties = autoclass('java.util.Properties')
        
        # Setup connection properties  
        db_path = Path(self.db_file).absolute()
        jdbc_url = f"jdbc:h2:{db_path};AUTO_SERVER=TRUE"
        props = Properties()
        props.setProperty("user", "sa") 
        props.setProperty("password", "")

        # Create connection
        self.connection = DriverManager.getConnection(jdbc_url, props)

        # Initialize H2GIS spatial functions
        H2GISFunctions.load(self.connection)

        # Wrap connection with H2GIS utilities
        self.connection = self.java_bridge.ConnectionWrapper(self.connection)
    
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

    def execute(self, sql: str, is_query: bool = False) -> None:
        """Execute SQL statement.
        
        Args:
            sql (str): SQL statement to execute
            is_query (bool): True if the SQL statement is a query, False otherwise
        """
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