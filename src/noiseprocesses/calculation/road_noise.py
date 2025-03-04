from noiseprocesses.protocols import (
    EmissionCalculator, PropagationCalculator, GridGenerator
)
from noiseprocesses.core.database import NoiseDatabase

class RoadNoiseModellingCalculator:
    """Main class handling the complete noise calculation process"""
    
    def __init__(
        self,
        emission_calculator: EmissionCalculator,
        propagation_calculator: PropagationCalculator,
        grid_generator: GridGenerator,
        database_name: str
    ):
        self.emission_calculator = emission_calculator
        self.propagation_calculator = propagation_calculator
        self.grid_generator = grid_generator
        self.database = NoiseDatabase(database_name)

    def calculate_noise_levels(
        self,
        source_table: str,
        receivers_table: str,
        buildings_table: str,
        **kwargs
    ) -> str:
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
        # Calculate emissions first
        emission_table = self.emission_calculator.calculate_emissions(source_table)
        
        # Use emission results for propagation
        result_table = self.propagation_calculator.calculate_propagation(
            emission_table=emission_table,
            receivers_table=receivers_table,
            buildings_table=buildings_table,
            **kwargs
        )
        
        return result_table
