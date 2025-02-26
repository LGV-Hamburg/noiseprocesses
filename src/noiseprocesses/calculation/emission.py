from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass
from sqlalchemy import Table, Column, MetaData
from ..core.database import NoiseDatabase

@dataclass
class EmissionConfig:
    """Base configuration for noise emission calculations."""
    coefficient_version: int = 2  # CNOSSOS-EU version
    temperature: float = 20.0     # Default temperature in °C

class EmissionSource(ABC):
    """Base class for noise emission sources."""
    
    def __init__(self, database: NoiseDatabase, config: Optional[EmissionConfig] = None):
        self.database = database
        self.config = config or EmissionConfig()
        self.metadata = MetaData()
        
        # Initialize NoiseModelling config
        self.lden_config = self.database.java_bridge.LDENConfig(
            self.database.java_bridge.LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
        )
        self.lden_config.setCoefficientVersion(self.config.coefficient_version)
    
    @abstractmethod
    def setup_source_table(self, geometry_file: str, **kwargs) -> str:
        """Setup source geometries and properties."""
        pass
    
    @abstractmethod
    def calculate_emissions(self, source_table: str) -> str:
        """Calculate noise emissions for the source."""
        pass
    
    def _create_table(self, table: Table) -> None:
        """Create a database table from SQLAlchemy definition."""
        columns = [f"{col.name} {col.type.compile()}" for col in table.columns]
        self.database.execute(f"""
            DROP TABLE IF EXISTS {table.name};
            CREATE TABLE {table.name} (
                {','.join(columns)}
            )
        """)

class EmissionProcessor:
    """Handles emission calculations for multiple sources."""
    
    FREQUENCY_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    TIME_PERIODS = ['D', 'E', 'N']
    
    def __init__(self, database: NoiseDatabase):
        self.database = database
        
    def get_emission_columns(self) -> List[str]:
        """Get standard emission column names."""
        return [f"LW{period}{freq}" 
                for period in self.TIME_PERIODS 
                for freq in self.FREQUENCY_BANDS]
    
    def process_emissions(self, source_table: str, 
                         emission_table: str,
                         lden_config: 'LDENConfig') -> None:
        """Process emissions for all sources in table."""
        # Initialize emission processor
        emission_processor = self.database.java_bridge.LDENPropagationProcessData(
            None, lden_config
        )
        
        # Get source records
        results = self.database.query(f"SELECT * FROM {source_table}")
        
        # Process each source
        for source in results:
            emissions = emission_processor.computeLw(source)
            self._insert_emission_results(
                emission_table,
                source['PK'], 
                source['THE_GEOM'], 
                emissions
            )
    
    def _insert_emission_results(self, table: str, pk: str, 
                               geom: str, emissions: list) -> None:
        """Insert emission calculation results."""
        day, evening, night = emissions
        self.database.execute(f"""
            INSERT INTO {table} (
                PK, THE_GEOM, 
                {', '.join(self.get_emission_columns())}
            )
            VALUES (
                '{pk}', '{geom}',
                {', '.join(str(val) for val in day + evening + night)}
            )
        """)