from typing import Protocol
class PropagationCalculator(Protocol):
    """Protocol defining propagation calculation interface"""
    def calculate_propagation(self, emission_table: str, receivers_table: str) -> str:
        """Calculate propagation and return result table name"""
        pass

class RoadPropagationCalculator:
    """Handles road noise propagation calculations"""
    
    def __init__(self, database: "NoiseDatabase", config: dict):
        self.database = database
        self.config = config

    def calculate_propagation(
        self,
        emission_table: str,
        receivers_table: str,
        buildings_table: str,
        **kwargs
    ) -> str:
        # Implementation of road propagation calculation
        pass
