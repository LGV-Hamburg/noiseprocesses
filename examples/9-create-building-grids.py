from pathlib import Path

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import BuildingGridConfig2d, BuildingGridConfig3d
from noiseprocesses.utils.buildings_grids import (
    BuildingGridGenerator2d,
    BuildingGridGenerator3d,
)

# Initialize database connection
db = NoiseDatabase(db_file="noise_db")

# Import buildings shapefile if not already imported
buildings_path = Path("examples/buildings-user.geojson")
if buildings_path.exists():
    print("Importing buildings shapefile...")
    db.import_geojson(
        str(buildings_path), "BUILDINGS",
        crs="http://www.opengis.net/def/crs/EPSG/0/25832"
    )

# Show some data from the 2D grid
results = db.query(
    f"SELECT PK, ST_AsText(THE_GEOM) as geometry FROM BUILDINGS LIMIT 2"
)
print("\n2D Receivers Data:")
for row in results:
    print(f"PK: {row[0]}, Geometry: {row[1]}")

# Example 1: Generate a 2D building grid
config_2d = BuildingGridConfig2d(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS",
    distance_from_wall=2.0,  # 2 meters from building facades
    receiver_distance=10.0,  # 10-meter spacing between receivers
    calculation_height_2d=10.0,  # 10 meters above ground
)

generator_2d = BuildingGridGenerator2d(db)
receivers_2d_table = generator_2d.generate_receivers(config_2d)
print(f"2D building grid created: {receivers_2d_table}")

# Show some data from the 2D grid
results = db.query(
    f"SELECT PK, ST_AsText(THE_GEOM) as geometry FROM {receivers_2d_table} LIMIT 10"
)
print("\n2D Receivers Data:")
for row in results:
    print(f"PK: {row[0]}, Geometry: {row[1]}")

# Example 2: Generate a 3D building grid
config_3d = BuildingGridConfig3d(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS_3D_GRID",
    distance_from_wall=2.0,  # 2 meters from building facades
    height_between_levels_3d=2.5,  # 2.5 meters between levels
    receiver_distance=10.0,  # 10-meter spacing between receivers
)

generator_3d = BuildingGridGenerator3d(db)
receivers_3d_table = generator_3d.generate_receivers(config_3d)
print(f"3D building grid created: {receivers_3d_table}")

# Show some data from the 3D grid
results = db.query(
    f"SELECT PK, ST_AsText(THE_GEOM) as geometry FROM {receivers_3d_table} LIMIT 10"
)
print("\n3D Receivers Data:")
for row in results:
    print(f"PK: {row[0]}, Geometry: {row[1]}")

# Clean up
db.disconnect()
