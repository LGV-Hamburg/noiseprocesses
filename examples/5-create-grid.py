from pathlib import Path
from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.models.grid_config import RegularGridConfig, DelaunayGridConfig
from noiseprocesses.utils.grids import RegularGridGenerator, DelaunayGridGenerator

# Initialize database connection
db = NoiseDatabase(
    db_file="noise_db",
)

# Example 1: Basic grid with buildings
basic_config = RegularGridConfig(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS_GRID",
    delta=10,  # 10-meter grid spacing
    height=2.75,  # 4 meters receiver height
    create_triangles=False
)

buildings_path = Path("dist/resources/org/noise_planet/noisemodelling/wps/buildings.shp")
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
        print("\n{:<15} {:<10} {:<30}".format(
            "Building ID", "Height", "Geometry"
        ))
        print("-" * 70)
        # Print data rows
        for index, row in enumerate(results):
            print("{:<15} {:<10} {:<30}".format(
                row[0], row[1],
                row[2][:30] + "..." if len(row[2]) > 30 else row[2]
            ))
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
    print("\n{:>6} {:<6} {:>6} {:<30}".format(
        "ID COL", "ID Row", "PK", "Geometry"
    ))
    print("-" * 70)
    # Print data rows
    for index, row in enumerate(results):
        print("{:>6} {:>6} {:>6} {:<30}".format(
            row[0], row[1], row[2], 
            row[3][:30] + "..." if len(row[3]) > 30 else row[3]
        ))
        if index == 10:
            break


delaunay_config = DelaunayGridConfig(
    buildings_table="BUILDINGS",
    output_table="RECEIVERS_GRID",
    height=2.75,  # 4 meters receiver height
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
    SELECT ID_COL, ID_ROW, PK,
        ST_AsText(THE_GEOM) as geometry
    FROM RECEIVERS_GRID
""")

if results:
    # Print header
    print("\n{:<15} {:<15} {:<10} {:<30}".format(
        "ID COL", "ID Row", "PK", "Geometry"
    ))
    print("-" * 70)
    # Print data rows
    for row in results:
        print("{:<15} {:<15} {:<10.1f} {:<30}".format(
            row[0], row[1], float(row[2]), 
            row[3][:30] + "..." if len(row[3]) > 30 else row[3]
        ))

# Clean up
db.disconnect()
