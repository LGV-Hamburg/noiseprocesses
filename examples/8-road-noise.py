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


request_body = {
    "inputs": {
        "buildings": buildings,
        "roads": roads_traffic,
        "crs": "http://www.opengis.net/def/crs/EPSG/0/25832",
    },
    "outputs": {
        # "noise_evening": {},
        # "noise_night": {},
        "noise_den": {},
    },
}
response = requests.post(
    "http://localhost:8000/processes/traffic_noise_propagation/execution",
    json=request_body,
)

print(response.status_code)
print(response.json())
