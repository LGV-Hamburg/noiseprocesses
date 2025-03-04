from typing import Protocol
from noiseprocesses.models.grid_config import RegularGridConfig 

class EmissionCalculator(Protocol):
    """Protocol defining emission calculation interface"""

    def calculate_emissions(self, source_table: str) -> str:
        """Calculate emissions and return result table name"""
        ...

    def create_emission_table(self, table_name: str) -> None:
        """Create emission results table"""
        ...

class PropagationCalculator(Protocol):
    """Protocol defining propagation calculation interface"""
    def calculate_propagation(
            self,
            emission_table: str,
            receivers_table: str,
            buildings_table: str,
    ) -> str:
        """Calculate propagation and return result table name"""
        ...

class GridGenerator(Protocol):
    """Protocol for grid generation strategies"""
    def generate_receivers(self, config: RegularGridConfig) -> str:
        """Generate receivers grid and return table name"""
        ...
