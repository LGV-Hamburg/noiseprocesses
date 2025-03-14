from pathlib import Path

from noiseprocesses.calculation.road_propagation import RoadPropagationCalculator
from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import DelaunayGridConfig, RegularGridConfig
from noiseprocesses.models.noise_calculation_config import NoiseCalculationConfig
from noiseprocesses.utils.contouring import IsoSurfaceBezier
from noiseprocesses.utils.grids import DelaunayGridGenerator, RegularGridGenerator

config = NoiseCalculationConfig()

db = NoiseDatabase(config.database.name, in_memory=False)

print(config)

# import buildings -> BUILDINGS
buildings_path = Path(
    "dist/resources/org/noise_planet/noisemodelling/wps/buildings.shp"
)
if buildings_path.exists():
    print("\nImporting buildings data...")
    db.import_shapefile(str(buildings_path), "buildings")

# create reveicer grid -> RECEIVERS
print("generating receivers grid")
grid_config = DelaunayGridConfig(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS",
    calculation_height=2.75,  # 4 meters receiver height
    create_triangles=True,
)

grid_generator = DelaunayGridGenerator(db)
receivers_table = grid_generator.generate_receivers(grid_config)

# import roads -> ROADS_TRAFFIC
print("\nImporting roads data...")
db.import_shapefile(
    "dist/resources/org/noise_planet/noisemodelling/wps/ROADS2.shp", "ROADS_TRAFFIC"
)

# roads_collection = {
#     "type": "FeatureCollection",
#     "features": [
#         {
#             "type": "Feature",
#             "properties": {
#                 "LV_D": 100,
#                 "LV_SPD_D": 50
#             },
#             "geometry": {
#                 "type": "LineString",
#                 "coordinates": [[0,0], [1,1]]
#             }
#         }
#     ]
# }

# db.import_geojson(roads_collection, "ROADS_TRAFFIC")

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
print("\nTable structure LDEN_RESULT:")
print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
print("-" * 50)
for col in columns:
    print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))

columns = db.query("SHOW COLUMNS FROM TRIANGLES")
print("\nTable structure TRIANGLES:")
print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
print("-" * 50)
for col in columns:
    print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))

surface_generator = IsoSurfaceBezier(db)

surface_generator.generate_iso_surface()

db.export_data("CONTOURING_NOISE_MAP")
