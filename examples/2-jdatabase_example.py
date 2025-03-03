from pathlib import Path

from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.core.java_bridge import JavaBridge


def test_database():
    try:
        print("1. Initializing Java bridge...")
        java_bridge = JavaBridge.get_instance()

        print("\n2. Setting up H2GIS database...")
        db = NoiseDatabase("my_calculation")
        # Clear any existing tables
        db.drop_all_tables()

        print("\n3. Testing spatial functionality...")
        # Create a simple spatial table
        db.execute("""
            CREATE TABLE test_geom (
                id INTEGER PRIMARY KEY,
                geom GEOMETRY
            )
        """)
        
        # Insert a point
        db.execute("""
            INSERT INTO test_geom VALUES 
            (1, ST_GeomFromText('POINT(10 10)'))
        """)

        print("\n4. Testing NoiseModelling configuration...")
        lden_config = java_bridge.LDENConfig(
            java_bridge.LDENConfig_INPUT_MODE.INPUT_MODE_TRAFFIC_FLOW
        )
        lden_config.setComputeLDay(True)
        print("LDEN Config created successfully")

        # Optional: Import sample data if exists
        buildings_path = Path("dist/resources/org/noise_planet/noisemodelling/wps/buildings.shp")
        if buildings_path.exists():
            print("\n5. Importing sample buildings shapefile...")
            db.import_shapefile(str(buildings_path), "buildings")
            # Count buildings
            db.execute("SELECT COUNT(*) FROM buildings")
            print(f"Imported {db.fetch_one()[0]} buildings")

        geojson_path = Path("examples/buildings.geojson")
        if geojson_path.exists():
            print("\n6. Testing GeoJSON import...")
            db.import_geojson(str(geojson_path), "buildings_geojson")
            
            # Show table structure
            columns = db.query("SHOW COLUMNS FROM buildings_geojson")
            print("\nTable structure:")
            print("{:<20} {:<20} {:<10}".format("Column", "Type", "Nullable"))
            print("-" * 50)
            for col in columns:
                print("{:<20} {:<20} {:<10}".format(col[0], col[1], col[2]))
            
            # Show actual data
            print("\nImported buildings data:")
            results = db.query("""
                SELECT building_id, building_type, height, 
                       ST_AsText(THE_GEOM) as geometry
                FROM buildings_geojson
            """)
            
            if results:
                # Print header
                print("\n{:<15} {:<15} {:<10} {:<30}".format(
                    "Building ID", "Type", "Height", "Geometry"
                ))
                print("-" * 70)
                # Print data rows
                for row in results:
                    print("{:<15} {:<15} {:<10.1f} {:<30}".format(
                        row[0], row[1], float(row[2]), 
                        row[3][:30] + "..." if len(row[3]) > 30 else row[3]
                    ))

        print("\nAll tests completed successfully!")
        db.disconnect()
        
    except Exception as e:
        print(f"Error in database test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database()