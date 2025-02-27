from pathlib import Path
import jnius_config
import os
from typing import Optional

class JavaBridge:
    """Manages JVM initialization and class loading for NoiseModelling."""
    
    _instance: Optional['JavaBridge'] = None
    
    def __init__(self):
        if JavaBridge._instance is not None:
            raise RuntimeError("JavaBridge is a singleton. Use JavaBridge.get_instance()")
        
        # Get path to NoiseModelling libraries
        current_dir = Path(__file__).parent
        lib_dir = (current_dir.parent.parent.parent / 'dist' / 'lib').resolve()
        
        # Configure JVM
        jnius_config.add_options('-Xmx4096m')
        classpath = str(lib_dir / '*')
        jnius_config.set_classpath(classpath)
        
        # Initialize commonly used classes
        self._init_classes()
    
    @classmethod
    def get_instance(cls) -> 'JavaBridge':
        if cls._instance is None:
            cls._instance = JavaBridge()
        return cls._instance
    
    def _init_classes(self):
        """Initialize commonly used Java classes."""
        from jnius import autoclass
        
        # Core classes
        self.File = autoclass('java.io.File')
        self.DBUtils = autoclass('org.h2gis.utilities.dbtypes.DBUtils')
        self.LDENConfig = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig')
        self.LDENConfig_INPUT_MODE = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig$INPUT_MODE')
        self.LDENConfig_TIME_PERIOD = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig$TIME_PERIOD')
        self.LDENPropagationProcessData = autoclass('org.noise_planet.noisemodelling.jdbc.LDENPropagationProcessData')
        self.PropagationProcessPathData = autoclass('org.noise_planet.noisemodelling.propagation.PropagationProcessPathData')
        
        # Database related
        self.ConnectionWrapper = autoclass('org.h2gis.utilities.wrapper.ConnectionWrapper')
        self.GeoJsonDriverFunction = autoclass('org.h2gis.functions.io.geojson.GeoJsonDriverFunction')
        self.TableLocation = autoclass('org.h2gis.utilities.TableLocation')
        
        # Utility classes
        self.EmptyProgressVisitor = autoclass('org.h2gis.api.EmptyProgressVisitor')
        self.PowerUtils = autoclass('org.noise_planet.noisemodelling.pathfinder.utils.PowerUtils')

        self.DriverManager = autoclass('java.sql.DriverManager')
        self.H2GISFunctions = autoclass('org.h2gis.functions.factory.H2GISFunctions')
        self.Properties = autoclass('java.util.Properties')

        self.GeometryTableUtilities = autoclass('org.h2gis.utilities.GeometryTableUtilities')

        self.JDBCUtilities = autoclass('org.h2gis.utilities.JDBCUtilities')

        # Add spatial result set classes
        self.SpatialResultSet = autoclass('org.h2gis.utilities.SpatialResultSet')
