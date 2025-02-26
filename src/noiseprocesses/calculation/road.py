from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.types import Double, Integer, String

from noiseprocesses.calculation.emission import (
    EmissionConfig,
    EmissionProcessor,
    EmissionSource,
)
from noiseprocesses.core.database import NoiseDatabase


@dataclass
class RoadCalculationConfig(EmissionConfig):
    """Configuration for road noise calculations."""
    coefficient_version: int = 2
    default_temp: float = 20.0
    default_pavement: str = "NL08"
    max_distance: float = 1000    # Maximum propagation distance
    max_reflection_order: int = 1 # Maximum number of reflections
    wall_absorption: float = 0.1  # Wall absorption coefficient
    max_angle: float = 180.0     # Maximum angle between source and receiver

class RoadNoiseCalculator(EmissionSource):
    """Handles road noise emission calculations."""
    
    def __init__(self, database: NoiseDatabase, 
                 config: Optional[RoadCalculationConfig] = None):
        super().__init__(database, config)
        self.processor = EmissionProcessor(database)
        self._init_tables()
    
    def _init_tables(self) -> None:
        """Initialize SQL table definitions matching CNOSSOS format."""
        self.roads = Table(
            'ROADS', self.metadata,
            Column('PK', Integer, primary_key=True),
            Column('THE_GEOM', String, nullable=False),
            # Vehicle counts - Day/Evening/Night periods
            *[Column(f"{vtype}_{period}", Double, server_default='0.0')
              for vtype in ['LV', 'MV', 'HGV', 'WAV', 'WBV']
              for period in ['D', 'E', 'N']],
            # Vehicle speeds
            *[Column(f"{vtype}_SPD_{period}", Double, server_default='0.0')
              for vtype in ['LV', 'MV', 'HGV', 'WAV', 'WBV']
              for period in ['D', 'E', 'N']],
            # Road properties
            Column('PVMT', String, server_default="'NL08'"),
            *[Column(f"TEMP_{period}", Double, server_default='20.0')
              for period in ['D', 'E', 'N']],
            Column('TS_STUD', Double, server_default='0.0'),
            Column('PM_STUD', Double, server_default='0.0'),
            Column('JUNC_DIST', Double),
            Column('JUNC_TYPE', Integer),
            Column('SLOPE', Double),
            Column('WAY', Integer, server_default='3')
        )

        self.emissions = Table(
            'LW_ROADS', self.metadata,
            Column('PK', Integer, primary_key=True),
            Column('THE_GEOM', String, nullable=False),
            *[Column(f"LW{period}{freq}", Double)
              for period in ['D', 'E', 'N']
              for freq in [63, 125, 250, 500, 1000, 2000, 4000, 8000]]
        )

    def setup_calculation(self, roads_input: str) -> str:
        """Setup road table for calculation from input source."""
        # Import road geometries with their properties
        self.database.import_data(roads_input, "ROADS")
        
        # Ensure all required columns exist with default values
        self._ensure_required_columns()
        
        return "ROADS"

    def _ensure_required_columns(self) -> None:
        """Ensure all required columns exist with proper defaults."""
        for column in self.roads.columns:
            if column.name not in ['PK', 'THE_GEOM']:
                self.database.add_column_if_not_exists(
                    'ROADS', 
                    column.name, 
                    column.type,
                    column.server_default
                )

    def calculate_emissions(self, roads_table: str = "ROADS") -> str:
        """Calculate road noise emissions."""
        # Initialize LDEN configuration
        lden_config = self._init_lden_config()
        
        # Create emission table
        self._create_emission_table()
        
        # Calculate emissions for each road segment
        self._process_emissions(roads_table, lden_config)
        
        # Update Z coordinates and ensure primary key
        self.database.execute("""
            UPDATE LW_ROADS SET THE_GEOM = ST_UPDATEZ(THE_GEOM, 0.05);
            ALTER TABLE LW_ROADS ALTER COLUMN PK INT NOT NULL;
            ALTER TABLE LW_ROADS ADD PRIMARY KEY (PK);
        """)
        
        return "LW_ROADS"

    def _create_emission_table(self) -> None:
        """Create the emission results table."""
        columns = [f"{col.name} {col.type.compile()}" 
                  for col in self.emissions.columns]
        self.database.execute(f"""
            DROP TABLE IF EXISTS LW_ROADS;
            CREATE TABLE LW_ROADS (
                {','.join(columns)}
            )
        """)
    
    def _process_emissions(self, roads_table: str, 
                          lden_config: 'LDENConfig') -> None:
        """Process emissions for all road segments."""
        # Get road records
        results = self.database.query(f"SELECT * FROM {roads_table}")
        
        # Initialize emission processor
        emission_processor = self.database.java_bridge.LDENPropagationProcessData(
            None, lden_config
        )
        
        # Process each road
        for road in results:
            emissions = emission_processor.computeLw(road)
            self._insert_emission_results(road['PK'], road['THE_GEOM'], emissions)
    
    def _insert_emission_results(self, pk: str, geom: str, 
                               emissions: list) -> None:
        """Insert emission calculation results into database."""
        day, evening, night = emissions
        self.database.execute(f"""
            INSERT INTO LW_ROADS (PK, THE_GEOM, 
                {', '.join(self._get_emission_columns())})
            VALUES (
                '{pk}', '{geom}',
                {', '.join(str(val) for val in day + evening + night)}
            )
        """)
    
    def _init_lden_config(self) -> 'LDENConfig':
        """Initialize LDEN configuration."""
        lden_config = self.database.java_bridge.LDENConfig(
            self.database.java_bridge.LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
        )
        lden_config.setCoefficientVersion(self.config.coefficient_version)
        return lden_config