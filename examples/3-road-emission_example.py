import logging

from noiseprocesses.calculation.road import RoadNoiseCalculator
from noiseprocesses.core.database import NoiseDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_road_emission():
    db = NoiseDatabase()
    try:
        # Import roads and calculate emissions
        db.import_geojson("examples/roads.geojson", "ROADS_TRAFFIC", crs=2154)
        calculator = RoadNoiseCalculator(db)
        emissions_table = calculator.calculate_emissions("ROADS_TRAFFIC")
        
        # Show results for all frequency bands
        results = db.query(f"""
            SELECT 
                PK,
                -- Day levels for all frequency bands
                LWD63, LWD125, LWD250, LWD500, 
                LWD1000, LWD2000, LWD4000, LWD8000,
                -- Evening levels
                LWE63, LWE125, LWE250, LWE500,
                LWE1000, LWE2000, LWE4000, LWE8000,
                -- Night levels
                LWN63, LWN125, LWN250, LWN500,
                LWN1000, LWN2000, LWN4000, LWN8000
            FROM {emissions_table}
            ORDER BY LWD1000 DESC
        """)
        
        # Print summary (1 kHz band as reference)
        print("\nEmission Results (1 kHz band):")
        print("{:<10} {:<15} {:<15} {:<15}".format(
            "Road ID", "Day 1kHz (dB)", "Evening 1kHz (dB)", "Night 1kHz (dB)"
        ))
        print("-" * 55)
        for row in results:
            pk = row[0]
            day_1khz = row[5]     # LWD1000
            eve_1khz = row[13]    # LWE1000
            night_1khz = row[21]  # LWN1000
            print("{:<10} {:<15.1f} {:<15.1f} {:<15.1f}".format(
                pk, day_1khz, eve_1khz, night_1khz
            ))
        
    except Exception as e:
        logging.error("Error in road emission calculation", exc_info=True)
    finally:
        if 'database' in locals():
            db.disconnect()

if __name__ == "__main__":
    test_road_emission()
