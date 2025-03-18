from typing import Self
from geojson_pydantic import Feature, FeatureCollection, Polygon
from pydantic import BaseModel, Field


class BuildingPropertiesInternal(BaseModel):
    id: int | str
    height: float = Field(alias="building_height")

    @classmethod
    def from_user_model(cls, user_model: 'BuildingProperties') -> Self:
        """Convert from user model to internal model."""
        # Pydantic v2 model_dump() with by_alias=True converts to internal field names
        return cls(**user_model.model_dump())


class BuildingProperties(BaseModel):
    id: int | str
    building_height: float

    def to_internal(self) -> BuildingPropertiesInternal:
        """Convert to internal model."""
        return BuildingPropertiesInternal.from_user_model(self)

BuildingsFeatureCollection = FeatureCollection[
    Feature[Polygon, BuildingProperties]
]