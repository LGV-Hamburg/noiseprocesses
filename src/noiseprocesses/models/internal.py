from geojson_pydantic import (
    Feature,
    FeatureCollection,
    LineString,
    MultiLineString,
    Polygon,
)
from pydantic import model_validator

from noiseprocesses.models.building_properties import (
    BuildingPropertiesInternal, BuildingsFeatureCollection
)
from noiseprocesses.models.ground_absorption import GroundAbsorptionInternal
from noiseprocesses.models.roads_properties import (
    CnossosTrafficFlow, RoadsFeatureCollection
)
from noiseprocesses.models.ground_absorption import (
    GroundAbsorptionInternal, GroundAbsorptionFeatureCollection
)

class RoadFeature(Feature[LineString | MultiLineString, CnossosTrafficFlow]):
    """A road feature with required traffic properties."""

    @model_validator(mode="after")
    def check_properties_exist(self) -> "RoadFeature":
        """Ensure properties are present."""
        if self.properties is None:
            raise ValueError("Road features must have traffic properties")
        return self


class RoadsFeatureCollectionInternal(FeatureCollection[RoadFeature]):
    """Internal feature collection using NoiseModelling parameter names."""

    @classmethod
    def from_user_collection(
        cls, user_collection: "RoadsFeatureCollection"
    ) -> "RoadsFeatureCollectionInternal":
        """Convert from user feature collection to internal format."""
        return cls(
            type="FeatureCollection",
            features=[
                RoadFeature(
                    geometry=feature.geometry,
                    properties=CnossosTrafficFlow.from_user_model(feature.properties),
                    id=feature.id,
                    type="Feature",
                )
                # skip features without properties, silently
                for feature in user_collection.features if feature.properties
            ],
        )


class BuildingsFeatureCollectionInternal(
    FeatureCollection[Feature[Polygon, BuildingPropertiesInternal]]
):
    @classmethod
    def from_user_collection(
        cls, user_collection: "BuildingsFeatureCollection"
    ) -> "BuildingsFeatureCollectionInternal":
        """Convert from user feature collection to internal format."""
        return cls(
            type="FeatureCollection",
            features=[
                Feature(
                    geometry=feature.geometry,
                    properties=BuildingPropertiesInternal.from_user_model(
                        feature.properties
                    ),
                    id=feature.id,
                    type="Feature",
                )
                # skip features without properties, silently
                for feature in user_collection.features if feature.properties
            ],
        )

GroundAbsorptionFeature = Feature[Polygon, GroundAbsorptionInternal]

class GroundAbsorptionFeatureCollectionInternal(
    FeatureCollection[GroundAbsorptionFeature]
):
    @classmethod
    def from_user_collection(
        cls, user_collection: "GroundAbsorptionFeatureCollection"
    ) -> "GroundAbsorptionFeatureCollectionInternal":
        """Convert from user feature collection to internal format."""
        return cls(
            type="FeatureCollection",
            features=[
                Feature(
                    geometry=feature.geometry,
                    properties=GroundAbsorptionInternal.from_user_model(
                        feature.properties
                    ),
                    id=feature.id,
                    type="Feature",
                )
                # skip features without properties, silently
                for feature in user_collection.features if feature.properties
            ],
        )

