from pathlib import Path
from noiseprocesses.calculation.road_propagation import RoadPropagationCalculator
from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import RegularGridConfig
from noiseprocesses.models.noise_calculation_config import NoiseCalculationConfig
from noiseprocesses.utils.grids import RegularGridGenerator

config = NoiseCalculationConfig()

db = NoiseDatabase(config.database_name, in_memory=True)

print(config)

# import buildings -> BUILDINGS
buildings_path = Path("dist/resources/org/noise_planet/noisemodelling/wps/buildings.shp")
if buildings_path.exists():
    print("\nImporting buildings data...")
    db.import_shapefile(str(buildings_path), "buildings")

# create reveicer grid -> RECEIVERS
print("generating receivers grid")
grid_config = RegularGridConfig(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS",
    delta=10,  # 10-meter grid spacing
    height=2.75,  # 4 meters receiver height
)

grid_generator = RegularGridGenerator(db)
receivers_table = grid_generator.generate_receivers(grid_config)

# import roads -> ROADS_TRAFFIC
print("\nImporting roads data...")
db.import_shapefile(
    "dist/resources/org/noise_planet/noisemodelling/wps/ROADS2.shp", "ROADS_TRAFFIC"
)

road_prop = RoadPropagationCalculator(db)

road_prop.calculate_propagation(config)

# List all tables in the database
print("\nTables in database:")
tables = db.query("""
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA='PUBLIC'
""")
for table in tables:
    print(f"- {table[0]}")

# Show table structure
columns = db.query("SHOW COLUMNS FROM LDEN_RESULT")
print("\nTable structure:")
print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
print("-" * 50)
for col in columns:
    print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))
