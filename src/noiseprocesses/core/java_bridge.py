from pathlib import Path
from typing import Optional
import jpype
import jpype.imports


class JavaBridge:
    """Manages JVM initialization and class loading for NoiseModelling."""

    _instance: Optional["JavaBridge"] = None

    def __init__(self):
        if JavaBridge._instance is not None:
            raise RuntimeError(
                "JavaBridge is a singleton. Use JavaBridge.get_instance()"
            )

        # Get path to NoiseModelling libraries
        current_dir = Path(__file__).parent
        lib_dir = (current_dir.parent.parent.parent / "dist" / "lib").resolve()

        # Configure and start JVM if not already running
        if not jpype.isJVMStarted():
            classpath = str(lib_dir / "*")
            jpype.startJVM(
                jpype.getDefaultJVMPath(),
                # Memory configuration
                "-Xmx4096m",           # Maximum heap size
                "-Xms1024m",           # Initial heap size
                
                # GC optimization
                "-XX:+UseG1GC",        # Use G1 garbage collector
                "-XX:MaxGCPauseMillis=200",  # Target max GC pause time
                
                # Database specific options
                "-Dh2.serverCachedObjects=3000",  # H2 object cache size
                "-Dh2.objectCacheMaxPerElementSize=4096",  # Max size per object
                "-Dh2.bigDecimalIsDecimal=true",  # Improved decimal handling
                
                # String optimization (important for GIS)
                "-XX:+OptimizeStringConcat",
                
                # Class path
                f"-Djava.class.path={classpath}",
                
                # JPype options
                convertStrings=True,    # Auto convert strings
                interrupt=True         # Allow thread interruption
            )
        
        # Initialize commonly used classes
        self._init_classes()

    @classmethod
    def get_instance(cls) -> "JavaBridge":
        if cls._instance is None:
            cls._instance = JavaBridge()
        return cls._instance

    @classmethod
    def shutdown(cls):
        if jpype.isJVMStarted():
            jpype.shutdownJVM()
        cls._instance = None
        
    def _init_classes(self):
        """Initialize commonly used Java classes."""
        # Using JPype's import style
        from java.io import File # type: ignore
        from java.sql import DriverManager # type: ignore
        from java.util import Properties # type: ignore
        
        from org.h2gis.utilities.dbtypes import DBUtils # type: ignore
        from org.h2gis.utilities.wrapper import ConnectionWrapper # type: ignore
        from org.h2gis.utilities import ( # type: ignore
            TableLocation, GeometryTableUtilities,
            JDBCUtilities, SpatialResultSet
        )
        from org.h2gis.functions.io.geojson import GeoJsonDriverFunction # type: ignore
        from org.h2gis.functions.factory import H2GISFunctions # type: ignore
        from org.h2gis.api import EmptyProgressVisitor # type: ignore
        
        from org.noise_planet.noisemodelling.jdbc import ( # type: ignore
            LDENConfig, LDENPropagationProcessData
        )
        from org.noise_planet.noisemodelling.propagation import ( # type: ignore
            PropagationProcessPathData
        )
        from org.noise_planet.noisemodelling.pathfinder.utils import ( # type: ignore
            PowerUtils
        )

        from org.h2gis.functions.io.asc import AscReaderDriver # type: ignore
        from org.h2gis.functions.io.geotiff import GeoTiffDriverFunction # type: ignore
        from org.h2gis.functions.spatial.crs import ST_SetSRID, ST_Transform # type: ignore
        from org.h2gis.functions.io.utility import PRJUtil # type: ignore
        from org.locationtech.jts.io import WKTReader, WKTWriter # type: ignore
        from org.noise_planet.noisemodelling.pathfinder import RootProgressVisitor # type: ignore
        
        # Store classes as instance attributes
        self.File = File
        self.DBUtils = DBUtils
        self.LDENConfig = LDENConfig
        self.LDENConfig_INPUT_MODE = LDENConfig.INPUT_MODE
        self.LDENConfig_TIME_PERIOD = LDENConfig.TIME_PERIOD
        self.LDENPropagationProcessData = LDENPropagationProcessData
        self.PropagationProcessPathData = PropagationProcessPathData
        
        self.ConnectionWrapper = ConnectionWrapper
        self.GeoJsonDriverFunction = GeoJsonDriverFunction
        self.TableLocation = TableLocation
        
        self.EmptyProgressVisitor = EmptyProgressVisitor
        self.PowerUtils = PowerUtils
        
        self.DriverManager = DriverManager
        self.H2GISFunctions = H2GISFunctions
        self.Properties = Properties
        
        self.GeometryTableUtilities = GeometryTableUtilities
        self.JDBCUtilities = JDBCUtilities
        self.SpatialResultSet = SpatialResultSet

        self.DriverManager = DriverManager
        self.AscReaderDriver = AscReaderDriver
        self.GeoTiffDriverFunction = GeoTiffDriverFunction
        self.ST_SetSRID = ST_SetSRID
        self.ST_Transform = ST_Transform
        self.PRJUtil = PRJUtil
        self.WKTReader = WKTReader
        self.WKTWriter = WKTWriter
        self.RootProgressVisitor = RootProgressVisitor