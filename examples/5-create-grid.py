from pathlib import Path

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import DelaunayGridConfig, RegularGridConfig
from noiseprocesses.utils.grids import DelaunayGridGenerator, RegularGridGenerator

# Initialize database connection
db = NoiseDatabase(
    db_file="noise_db",
)

# Example 1: Basic grid with buildings
basic_config = RegularGridConfig(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS_GRID",
    delta=10,  # 10-meter grid spacing
    calculation_height=2.75,  # 4 meters receiver height
    create_triangles=False,
)

buildings_path = Path(
    "dist/resources/org/noise_planet/noisemodelling/wps/buildings.shp"
)
if buildings_path.exists():
    print("\n6. Testing GeoJSON import...")
    db.import_shapefile(str(buildings_path), "buildings")

    # Show table structure
    columns = db.query(f"SHOW COLUMNS FROM {basic_config.buildings_table}")
    print("\nTable structure:")
    print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
    print("-" * 50)
    for col in columns:
        print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))

    # Show actual data
    print("\nImported buildings data:")
    results = db.query(
        f"""
            SELECT ID_WAY, HEIGHT, 
                ST_AsText(THE_GEOM) as geometry
            FROM {basic_config.buildings_table}
        """
    )
    if results:
        # Print header
        print("\n{:<15} {:<10} {:<30}".format("Building ID", "Height", "Geometry"))
        print("-" * 70)
        # Print data rows
        for index, row in enumerate(results):
            print(
                "{:<15} {:<10} {:<30}".format(
                    row[0], row[1], row[2][:30] + "..." if len(row[2]) > 30 else row[2]
                )
            )
            if index == 10:
                break

# Create grid generator
grid_generator = RegularGridGenerator(db)

receivers_table = grid_generator.generate_receivers(basic_config)
print(f"Created receivers grid: {receivers_table}")

# Show table structure
columns = db.query("SHOW COLUMNS FROM RECEIVERS_GRID")
print("\nTable structure:")
print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
print("-" * 50)
for col in columns:
    print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))

# Show actual data
print("\nReceivers data:")
results = db.query("""
    SELECT ID_COL, ID_ROW, PK,
        ST_AsText(THE_GEOM) as geometry
    FROM RECEIVERS_GRID
""")

if results:
    # Print header
    print("\n{:>6} {:<6} {:>6} {:<30}".format("ID COL", "ID Row", "PK", "Geometry"))
    print("-" * 70)
    # Print data rows
    for index, row in enumerate(results):
        print(
            "{:>6} {:>6} {:>6} {:<30}".format(
                row[0],
                row[1],
                row[2],
                row[3][:30] + "..." if len(row[3]) > 30 else row[3],
            )
        )
        if index == 10:
            break


################
### Delaunay ###
################

# import roads
db.import_geojson("examples/roads-user.geojson", "ROADS_TRAFFIC", crs=2154)

delaunay_config = DelaunayGridConfig(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS_GRID",
    calculation_height=2.75,  # 4 meters receiver height
    sources_table="ROADS_TRAFFIC",
    road_width=15,
)

delauny_generator = DelaunayGridGenerator(db)
receivers_table = delauny_generator.generate_receivers(delaunay_config)
print(f"Created receivers grid: {receivers_table}")

# Show table structure
columns = db.query("SHOW COLUMNS FROM RECEIVERS_GRID")
print("\nTable structure:")
print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
print("-" * 50)
for col in columns:
    print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))

# Show actual data
print("\nReceivers data:")
results = db.query("""
    SELECT PK, ST_AsText(THE_GEOM) as geometry
    FROM RECEIVERS_GRID
""")

if results:
    # Print header
    print("\n{:<15} {:<30}".format("PK", "Geometry"))
    print("-" * 70)
    # Print data rows
    for index, row in enumerate(results):
        print(
            "{:<15} {:<30}".format(
                row[0], row[1][:30] + "..." if len(row[1]) > 30 else row[1]
            )
        )
        if index == 10:
            break

print("\nReceivers triangles data:")
results = db.query("""
    SELECT PK, ST_AsText(THE_GEOM) as geometry,
        PK_1, PK_2, PK_3, CELL_ID
    FROM TRIANGLES
""")

if results:
    # Print header
    print(
        "\n{:<8} {:<35} {:>8} {:<15} {:<15} {:<15}".format(
            "PK", "Geometry", "PK1", "PK2", "PK3", "CELL_ID"
        )
    )
    print("-" * 70)
    # Print data rows
    for index, row in enumerate(results):
        print(
            "{:<8} {:<35} {:>8} {:<15} {:<15} {:<15}".format(
                row[0],
                row[1][:30] + "..." if len(row[1]) > 30 else row[1],
                row[2],
                row[3],
                row[4],
                row[5],
            )
        )
        if index == 10:
            break

# Clean up
db.disconnect()
