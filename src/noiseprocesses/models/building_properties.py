from pydantic import BaseModel, Field


class BuildingProperties(BaseModel):
    id: int | str
    building_height: float

class BuildingPropertiesInternal(BaseModel):
    id: int | str
    height: float = Field(alias="building_height")
