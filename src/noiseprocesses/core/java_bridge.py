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
        self.LDENConfig = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig')
        self.LDENConfig_INPUT_MODE = autoclass('org.noise_planet.noisemodelling.jdbc.LDENConfig$INPUT_MODE')
        
        # Database related
        self.ConnectionWrapper = autoclass('org.h2gis.utilities.wrapper.ConnectionWrapper')
        self.TableLocation = autoclass('org.h2gis.utilities.TableLocation')
        
        # Utility classes
        self.EmptyProgressVisitor = autoclass('org.h2gis.api.EmptyProgressVisitor')