from geojson_pydantic import Feature, LineString, MultiLineString, Polygon
from pydantic import AnyUrl, BaseModel, ConfigDict
from geojson_pydantic.features import FeatureCollection
from noiseprocesses.models.grid_config import GridSettingsUser
from noiseprocesses.models.isosurface_config import IsoSurfaceUserSettings
from noiseprocesses.models.noise_calculation_config import (
    AcousticParameters, PropagationSettings
)
from noiseprocesses.models.roads_properties import TrafficFlow
from noiseprocesses.models.building_properties import BuildingProperties
from noiseprocesses.models.ground_absorption import GroundAbsorption

BuildingsFeatureCollection = FeatureCollection[
    Feature[Polygon, BuildingProperties]
]
RoadsFeatureCollection = FeatureCollection[
    Feature[LineString | MultiLineString, TrafficFlow]
]
GroundAbsorptionFeatureCollection = FeatureCollection[
    Feature[Polygon, GroundAbsorption]
]

class PropagationUserInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    buildings: BuildingsFeatureCollection
    roads: RoadsFeatureCollection
    dem: AnyUrl | None = None
    ground_absorption: GroundAbsorptionFeatureCollection | None = None
    acoustic_parameters: AcousticParameters | None = None
    propagation_settings: PropagationSettings | None = None
    receiver_grid_settings: GridSettingsUser | None = None
    iosurface_settings: IsoSurfaceUserSettings | None = None


if __name__ == "__main__":

    buildings_geojson = {
    "type": "FeatureCollection",
    "numberReturned": 10,
    "numberMatched": 453223,
    "timeStamp": "2025-03-03T16:00:13Z",
    "features": [
    {
    "type": "Feature",
    "geometry": {
    "type": "Polygon",
    "coordinates": [
    [
    [
    10.225382,
    53.420556
    ],
    [
    10.225231,
    53.420594
    ],
    [
    10.225226,
    53.420586
    ],
    [
    10.225377,
    53.420548
    ],
    [
    10.225382,
    53.420556
    ]
    ]
    ]
    },
    "properties": {
    "id": "Building_DEHHALKA3wT000D2",
    "building_height": 3
    },
    "id": 1
    }]
    }

    buildings = BuildingsFeatureCollection(**buildings_geojson)
    pass

if __name__ == "__main__":

    import json
    schema = PropagationUserInput.model_json_schema()

    with open("schema.json", "w") as file:
        json.dump(schema, file, indent=4)
    
