from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, List, Any, Tuple
from sqlalchemy import Table, Column, MetaData, Text
from sqlalchemy.types import Double, Integer, String
from ..core.database import NoiseDatabase

@dataclass
class EmissionConfig:
    """Base configuration for noise emission calculations."""
    coefficient_version: int = 2
    default_temp: float = 20.0
    
    FREQUENCY_BANDS = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
    TIME_PERIODS = ['D', 'E', 'N']

class EmissionSource(ABC):
    """Base class for noise emission sources."""
    
    def __init__(self, database: NoiseDatabase, config: Optional[EmissionConfig] = None):
        self.database = database
        self.config = config or EmissionConfig()
        self.metadata = MetaData()
        
        # Initialize NoiseModelling config
        self.lden_config = self._init_lden_config()
    
    def _init_lden_config(self) -> Any:
        """Initialize LDEN configuration."""
        lden_config = self.database.java_bridge.LDENConfig(
            self.database.java_bridge.LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
        )
        lden_config.setCoefficientVersion(self.config.coefficient_version)
        
        # Configure periods without propagation
        PropagationProcessPathData = self.database.java_bridge.PropagationProcessPathData
        for period in ['DAY', 'EVENING', 'NIGHT']:
            lden_config.setPropagationProcessPathData(
                getattr(self.database.java_bridge.LDENConfig_TIME_PERIOD, period),
                PropagationProcessPathData(False)
            )
        return lden_config
    
    @abstractmethod
    def setup_source_table(self, geometry_file: str, **kwargs) -> str:
        """Setup source geometries and properties table."""
        pass
    
    @abstractmethod
    def calculate_emissions(self, source_table: str) -> str:
        """Calculate noise emissions and create results table."""
        pass
    
    def _create_emission_table(self, table_name: str) -> None:
        """Create standardized emission table using SQLAlchemy."""
        # Define table structure
        emission_table = Table(
            table_name, 
            self.metadata,
            Column('PK', Integer),
            Column('THE_GEOM', String),  # H2GIS GEOMETRY type maps to String
            *[
                Column(f'LW{period}{freq}', Double)
                for period in self.config.TIME_PERIODS
                for freq in self.config.FREQUENCY_BANDS
            ]
        )
        
        # Create table using existing method
        self._create_table(emission_table)
    
    def _create_table(self, table: Table) -> None:
        """Create a database table from SQLAlchemy definition."""
        columns = [f"{col.name} {col.type.compile()}" for col in table.columns]
        self.database.execute(f"""
            DROP TABLE IF EXISTS {table.name};
            CREATE TABLE {table.name} (
                {','.join(columns)}
            )
        """)