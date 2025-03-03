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
            jpype.startJVM(jpype.getDefaultJVMPath(), 
                          "-Xmx4096m", 
                          f"-Djava.class.path={classpath}",
                          convertStrings=True)
        
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
        from java.sql import DriverManager
        from java.util import Properties
        
        from org.h2gis.utilities.dbtypes import DBUtils
        from org.h2gis.utilities.wrapper import ConnectionWrapper
        from org.h2gis.utilities import TableLocation, GeometryTableUtilities, JDBCUtilities, SpatialResultSet
        from org.h2gis.functions.io.geojson import GeoJsonDriverFunction
        from org.h2gis.functions.factory import H2GISFunctions
        from org.h2gis.api import EmptyProgressVisitor
        
        from org.noise_planet.noisemodelling.jdbc import LDENConfig, LDENPropagationProcessData
        from org.noise_planet.noisemodelling.propagation import PropagationProcessPathData
        from org.noise_planet.noisemodelling.pathfinder.utils import PowerUtils
        
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