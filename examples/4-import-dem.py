from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.utils.raster import convert_to_asc_array

input_path = "examples/dgm1_32_556_9270_1_hh_2022.tif"
output_path = "examples/dgm1_32_556_9270_1_hh_2022.asc"

# Initialize database connection
db = NoiseDatabase(db_file="noise_project")

raster = convert_to_asc_array(input_path)

raster.dump_to_asc(output_path)

# Example 1: Import an ASC file
# Basic usage with default parameters
db.import_raster(
    file_path=output_path,
    output_table="DEM",
    srid=25832
)

# Example 2: Import GeoTIFF with downscaling
# This will reduce the resolution by a factor of 2
db.import_raster(
    file_path=input_path,
    output_table="TERRAIN",
    srid=25832,
    downscale=2
)

# # Example 3: Import with fence (spatial filter)
# # The fence is a WKT polygon string to limit the import area
# fence_wkt = """POLYGON((
#     2.3367 48.8589, 
#     2.3517 48.8589, 
#     2.3517 48.8689, 
#     2.3367 48.8689, 
#     2.3367 48.8589
# ))"""

# db.import_raster(
#     file_path="/path/to/dem.tif",
#     output_table="FILTERED_DEM",
#     srid=2154,  # French coordinate system (RGF93)
#     fence=fence_wkt,
#     downscale=1
# )

# Don't forget to close the connection when done
db.disconnect()