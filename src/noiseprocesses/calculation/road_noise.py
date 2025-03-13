from typing import Any, Dict
from noiseprocesses.calculation.road_propagation import RoadPropagationCalculator
from noiseprocesses.models.grid_config import DelaunayGridConfig
from noiseprocesses.models.internal import BuildingsFeatureCollectionInternal, RoadsFeatureCollectionInternal
from noiseprocesses.models.noise_calculation_config import NoiseCalculationConfig
from noiseprocesses.models.user_input import PropagationUserInput
from noiseprocesses.protocols import (
    PropagationCalculator, GridGenerator

)
from noiseprocesses.utils.grids import DelaunayGridGenerator
from noiseprocesses.core.database import NoiseDatabase

from fastprocesses.processes.process_registry import register_process
from fastprocesses.core.base_process import BaseProcess
from fastprocesses.core.models import (
    ProcessDescription,
    ProcessInput,
    ProcessJobControlOptions,
    ProcessOutput,
    ProcessOutputTransmission,
    Schema,
)

@register_process("simple_process")
class TrafficNoiseProcess(BaseProcess):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        pass


class RoadNoiseModellingCalculator:
    """Main class handling the complete noise calculation process"""
    
    def __init__(
        self,
        noise_calculation_config: NoiseCalculationConfig | None = None
    ):
        self.config = noise_calculation_config or NoiseCalculationConfig()
        
        self.database = NoiseDatabase(
            db_file=self.config.database.name,
            in_memory=self.config.database.in_memory
        )

    def calculate_noise_levels(
        self,
        user_input: PropagationUserInput
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
        # validate user inputs
            # - buildings user input -> buildings internal
        buildings = BuildingsFeatureCollectionInternal.from_user_collection(
            user_input.buildings
        )
            # - roads user input -> roads internal
        roads_traffic = RoadsFeatureCollectionInternal.from_user_collection(
            user_input.roads
        )
            # - ...

        # setup the database
        noise_db = NoiseDatabase(
            self.config.database.name,
            self.config.database.in_memory
        )

        # import data
            # - buildings -> geojson
        noise_db.import_geojson(
            buildings.model_dump(exclude_none=True), # omit empty fields like bbox
            self.config.required_tables.building_table
        )
            # - roads -> geojson
        noise_db.import_geojson(
            roads_traffic.model_dump(exclude_unset=True), # omit empty fields like bbox
            self.config.required_tables.roads_table
        )
            # - load dem -> tif
            # - grounds -> geojson

        # generate receivers (using Delaunay with triangle creation)
        grid_config = DelaunayGridConfig(
            buildings_table=self.config.required_tables.building_table,
            output_table=self.config.required_tables.receivers_table,
            height=2.75,  # 4 meters receiver height
            sources_table=self.config.required_tables.roads_table,
            road_width=15
        )

        delauny_generator = DelaunayGridGenerator(noise_db)
        delauny_generator.generate_receivers(grid_config)

        # calculate propagation
        road_prop = RoadPropagationCalculator(noise_db)
        road_prop.calculate_propagation(self.config)

        # create isocontour

        # export to dict/geojson/FeatureCollection
        
        return {}
