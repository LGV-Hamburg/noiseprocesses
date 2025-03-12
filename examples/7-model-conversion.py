from pathlib import Path
import json

from noiseprocesses.models.user_input import RoadsFeatureCollection
from noiseprocesses.models.internal import RoadsFeatureCollectionInternal

from pydantic import ValidationError

user_roads_path = Path("examples/roads-user.json")
roads = {}

with open(user_roads_path, "r") as file:
    roads = json.load(file)

try:
    roads_model_user = RoadsFeatureCollection.model_validate(roads)

    roads_model_internal = RoadsFeatureCollectionInternal.from_user_collection(
        roads_model_user
    )

    for road in roads_model_internal.features:
        print(road.properties)

except ValidationError as e:
    print(e)
