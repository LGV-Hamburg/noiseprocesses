import logging
from typing import Any, Dict

from fastprocesses.core.base_process import BaseProcess
from fastprocesses.core.models import (
    ProcessDescription,
    ProcessInput,
    ProcessJobControlOptions,
    ProcessOutput,
    ProcessOutputTransmission,
    Schema,
)
from fastprocesses.processes.process_registry import register_process

from noiseprocesses.calculation.road_propagation import RoadPropagationCalculator
from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import DelaunayGridConfig
from noiseprocesses.models.internal import (
    BuildingsFeatureCollectionInternal,
    RoadsFeatureCollectionInternal,
)
from noiseprocesses.models.noise_calculation_config import (
    NoiseCalculationConfig, NoiseCalculationUserInput
)
from noiseprocesses.utils.contouring import IsoSurfaceBezier
from noiseprocesses.utils.grids import DelaunayGridGenerator

logger = logging.getLogger(__name__)


@register_process("simple_process")
class TrafficNoiseProcess(BaseProcess):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        pass


class RoadNoiseModellingCalculator:
    """Main class handling the complete noise calculation process"""

    def __init__(self, noise_calculation_config: NoiseCalculationConfig | None = None):
        self.config = noise_calculation_config or NoiseCalculationConfig() # defaults

        self.database = NoiseDatabase(
            db_file=self.config.database.name, in_memory=self.config.database.in_memory
        )
        # match output control and table names:
        self.match_oct = {
            "noise_day": "LDAY_GEOM",
            "noise_evening": "LEVENING_GEOM",
            "noise_night": "LNIGHT_GEOM",
            "noise_den": "LDEN_GEOM",
        }

    def calculate_noise_levels(
        self,
        user_input: NoiseCalculationUserInput
    ) -> dict:
        """
        Calculate complete noise levels including emission and propagation

        Args:
            source_table: Name of source table (roads/railway)
            receivers_table: Name of receivers table
            buildings_table: Name of buildings table
            **kwargs: Additional calculation parameters

        Returns:
            str: Name of final results table
        """
        # config setup, take defaults if user did not provide any
        self.config.acoustic_params = (
            user_input.acoustic_parameters or self.config.acoustic_params
        )
        self.config.propagation_settings = (
            user_input.propagation_settings or self.config.propagation_settings
        )
        self.config.output_controls = (
            user_input.noise_output_controls or self.config.output_controls
        )
        self.config.receiver_grid_settings = (
            user_input.receiver_grid_settings or self.config.receiver_grid_settings
        )

        # validate user inputs
        # - buildings user input -> buildings internal
        buildings = BuildingsFeatureCollectionInternal.from_user_collection(
            user_input.buildings
        )
        # - roads user input -> roads internal
        roads_traffic = RoadsFeatureCollectionInternal.from_user_collection(
            user_input.roads
        )
        # - grounds

        # - dem

        # setup the database
        noise_db = NoiseDatabase(
            self.config.database.name, self.config.database.in_memory
        )

        # import data
        # - buildings -> geojson
        noise_db.import_geojson(
            buildings.model_dump(exclude_none=True),  # omit empty fields like bbox
            self.config.required_input.building_table,
        )
        # - roads -> geojson
        noise_db.import_geojson(
            roads_traffic.model_dump(exclude_unset=True),  # omit empty fields like bbox
            self.config.required_input.roads_table,
        )
        # - load dem -> tif
        # - grounds -> geojson

        # generate receivers (using Delaunay with triangle creation)
        # configure grid parameters
        # !currently only DelaunayGridConfig is supported!
        grid_config = DelaunayGridConfig(
            buildings_table=self.config.required_input.building_table,
            output_table=self.config.required_input.receivers_table,
            sources_table=self.config.required_input.roads_table,
        )
        if user_input.receiver_grid_settings:
            grid_config.height = self.config.receiver_grid_settings.calculation_height
            grid_config.max_area = self.config.receiver_grid_settings.max_area
            grid_config.max_cell_dist = self.config.receiver_grid_settings.max_cell_dist
            grid_config.road_width = self.config.receiver_grid_settings.road_width

        delauny_generator = DelaunayGridGenerator(noise_db)
        delauny_generator.generate_receivers(grid_config)

        # calculate propagation
        road_prop = RoadPropagationCalculator(noise_db)
        road_prop.calculate_propagation(self.config)

        # create isocontour
        surface_generator = IsoSurfaceBezier(noise_db)
        for output_table, output_control in self.config.output_controls:
            if output_control:

                table_name = surface_generator.generate_iso_surface(self.match_oct[output_table])

                # export to dict/geojson/FeatureCollection
                # H2 DB has no support for in-memory data export
                noise_db.export_data(table_name)

        return {}
