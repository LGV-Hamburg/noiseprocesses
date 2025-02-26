from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path
from sqlalchemy import Table, Column, MetaData, DDL, text
from sqlalchemy.types import Double, String
from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.traffic_flow import TrafficFlow
from noiseprocesses.calculation.emission import EmissionProcessor, EmissionConfig, EmissionSource


@dataclass
class RoadCalculationConfig(EmissionConfig):
    """Configuration for road noise calculations."""
    coefficient_version: int = 2  # CNOSSOS-EU version
    temperature: float = 20.0     # Default temperature in °C
    receivers_table: str = ""     # Table containing receiver points
    max_distance: float = 1000    # Maximum propagation distance
    max_reflection_order: int = 1 # Maximum number of reflections
    wall_absorption: float = 0.1  # Wall absorption coefficient
    max_angle: float = 180.0     # Maximum angle between source and receiver

class RoadNoiseCalculator(EmissionSource):
    """Handles both emission and propagation calculations for road noise."""
    
    def __init__(self, database: NoiseDatabase, 
                 config: Optional[RoadCalculationConfig] = None):
        super().__init__(database, config)
        self.processor = EmissionProcessor(database)
        self._init_tables()
    
    def _init_tables(self) -> None:
        """Initialize SQL table definitions."""
        self.roads_traffic = Table(
            'ROADS_TRAFFIC', self.metadata,
            Column('PK', String, primary_key=True),
            Column('THE_GEOM', String, nullable=False),
            *[Column(name, Double, server_default=text('0.0')) 
              for name in self._get_traffic_columns()]
        )
        
        self.emissions = Table(
            'LW_ROADS', self.metadata,
            Column('PK', String, primary_key=True),
            Column('THE_GEOM', String, nullable=False),
            *[Column(name, Double) 
              for name in self._get_emission_columns()]
        )
    
    def _get_traffic_columns(self) -> list[str]:
        """Get list of traffic-related column names."""
        vehicle_types = ['LV', 'MV', 'HGV', 'WAV', 'WBV']
        periods = ['D', 'E', 'N']
        columns = []
        
        # Traffic flow columns
        columns.extend(f"{vtype}_{period}" for vtype in vehicle_types 
                      for period in periods)
        
        # Speed columns
        columns.extend(f"{vtype}_SPD_{period}" for vtype in vehicle_types 
                      for period in periods)
        
        # Other parameters
        columns.extend(['PVMT', 'TEMP', 'SLOPE', 'WAY'])
        return columns
    
    def _get_emission_columns(self) -> list[str]:
        """Get list of emission-related column names."""
        periods = ['D', 'E', 'N']
        frequencies = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        return [f"LW{period}{freq}" for period in periods 
                for freq in frequencies]
    
    def setup_calculation(self, roads_geojson: str, 
                         traffic_data: Dict[str, TrafficFlow]) -> str:
        """Setup road geometries and traffic data for calculation."""
        # Import road geometries
        self.database.import_geojson(roads_geojson, "ROADS_TRAFFIC")
        
        # Add required columns
        for column in self.roads_traffic.columns:
            if column.name not in ['PK', 'THE_GEOM']:
                stmt = DDL(
                    'ALTER TABLE ROADS_TRAFFIC '
                    'ADD COLUMN IF NOT EXISTS {} {} DEFAULT {}'.format(
                        column.name,
                        column.type.compile(),
                        column.server_default.arg
                    )
                )
                self.database.execute(stmt)
        
        # Update traffic data
        self._update_traffic_data(traffic_data)
        return "ROADS_TRAFFIC"
    
    def _update_traffic_data(self, traffic_data: Dict[str, TrafficFlow]) -> None:
        """Update traffic data in the roads table."""
        for road_id, flow in traffic_data.items():
            values = {
                'LV_D': flow.light_vehicles,
                'MV_D': flow.medium_vehicles,
                'HGV_D': flow.heavy_vehicles,
                'WAV_D': flow.light_motorcycles,
                'WBV_D': flow.heavy_motorcycles,
                'LV_SPD_D': flow.light_speed,
                'MV_SPD_D': flow.medium_speed,
                'HGV_SPD_D': flow.heavy_speed,
                'WAV_SPD_D': flow.light_moto_speed,
                'WBV_SPD_D': flow.heavy_moto_speed,
                'PVMT': flow.pavement,
                'TEMP': flow.temperature
            }
            stmt = self.roads_traffic.update().where(
                self.roads_traffic.c.PK == road_id
            ).values(values)
            self.database.execute(stmt)
    
    def calculate_emissions(self, roads_table: str = "ROADS_TRAFFIC") -> str:
        """Calculate road noise emissions without propagation."""
        # Initialize NoiseModelling components
        lden_config = self.database.java_bridge.LDENConfig(
            self.database.java_bridge.LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
        )
        lden_config.setCoefficientVersion(self.config.coefficient_version)
        
        # Create emission table
        self._create_emission_table()
        
        # Calculate emissions for each road segment
        self._process_emissions(roads_table, lden_config)
        
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