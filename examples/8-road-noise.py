# !currently errors in execute() are not propgataed to the user!!
# pydantic_core._pydantic_core.ValidationError: 12 validation errors for NoiseCalculationUserInput
# roads.features.0.properties.id
#   Field required [type=missing, input_value={'PK': 68, 'OSM_ID': '236...0.0, 'pavement': 'NL05'}, input_type=dict]

# instead only logged to the celery app!
import requests
import json

buildings = {}
with open("examples/buildings-user.geojson") as f:
    buildings = json.load(f)

roads_traffic = {}
with open("examples/roads-user.geojson") as f:
    roads_traffic = json.load(f)

grounds = {}
with open("examples/grounds-user.geojson") as f:
    grounds = json.load(f)

dem_bbox_feature = {}
with open("examples/dem_bbox-user.geojson") as f:
    dem_bbox_feature = json.load(f)

request_body = {
    "inputs": {
        "buildings": buildings,
        "roads": roads_traffic,
        "crs": "http://www.opengis.net/def/crs/EPSG/0/25832",
        # "ground_absorption": grounds,
        "propagation_settings": {
            "vertical_diffraction": True, "horizontal_diffraction": True
        },
        "acoustic_parameters": {
            "max_source_distance": 147,
        },
        "building_grid_settings": {
            "height_between_levels_3d": 2.5,
            "grid_type": "BUILDINGS_3D",
            "receiver_height_2d": 4,
            "distance_from_wall": 2,
            "receiver_distance": 10,
            "join_receivers_by_xy_location_3d": True,
        },
        # "dem_bbox_feature": dem_bbox_feature,
        # "dem_url": "https://ump-lgv.germanywestcentral.cloudapp.azure.com/raster/dem5_hh/cog/bbox/566700,5934580,566800,5934680/500x500.tif?coord_crs=epsg:25832"
    },
    "outputs": {
        # "noise_evening": {},
        # "noise_night": {},
        "noise_den": {},
    },
}

alternative_request_body = None
# with open("examples/example-request-body.json") as f:
#     alternative_request_body = json.load(f)

if alternative_request_body:
    request_body = alternative_request_body

url = "https://ump-lgv.germanywestcentral.cloudapp.azure.com/api/processes/noise_v4:traffic_noise_propagation/execution"
url = "http://localhost:8000/processes/traffic_noise_propagation/execution"
url = "http://localhost:8000/processes/traffic_noise_buildings/execution"
# url = "https://ump-lgv.germanywestcentral.cloudapp.azure.com/api/processes/noise_v4:traffic_noise_buildings/execution"

response = requests.post(
    url,
    json=request_body,
)

print(response.status_code)
print(response.json())
