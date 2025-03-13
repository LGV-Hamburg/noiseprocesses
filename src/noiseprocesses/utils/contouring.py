import logging

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.core.java_bridge import JavaBridge
from noiseprocesses.models.isosurface_config import IsoSurfaceConfig, IsoSurfaceUserSettings

logger = logging.getLogger(__name__)


class IsoSurfaceBezier:
    def __init__(
        self,
        database: NoiseDatabase,
        user_config: IsoSurfaceUserSettings | None = None
    ):
        self.database = database
        self.java_bridge = JavaBridge.get_instance()
        self.target_srid = 0
        self.config = self._init_config(user_config)

    def _init_config(self, config: IsoSurfaceUserSettings | None = None):
        if config:
            return IsoSurfaceConfig.model_validate(config)
        
        return IsoSurfaceConfig()

    def generate_iso_surface(self):
        logger.info("Starting isosurface generation.")

        srid = 0
        TableLocation = self.java_bridge.TableLocation

        srid = self.java_bridge.GeometryTableUtilities.getSRID(
            self.database.connection, TableLocation.parse(
                self.config.noise_level_table.value
            )
        )

        iso_levels = self.java_bridge.BezierContouring.NF31_133_ISO
        if self.config.iso_classes:
            
            iso_levels = self.java_bridge.ArrayList()
            
            # Add each element from the Python list
            for item in self.config.iso_classes:
                iso_levels.add(self.java_bridge.JFloat(item))  # Use JFloat for double values

        bezier = self.java_bridge.BezierContouring(iso_levels, srid)

        bezier.setPointTable(
            self.config.noise_level_table.value
        )

        bezier.setSmoothCoefficient(0.5)
        bezier.setSmooth(False) if (
            self.config.smooth_coefficient < 0.01
        ) else (
            bezier.setSmooth(True)
        )

        bezier.createTable(self.database.connection)

        logger.info(f"Contouring table {bezier.getOutputTable()} created.")
