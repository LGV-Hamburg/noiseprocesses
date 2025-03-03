from pydantic import BaseModel


class BuildingProperties(BaseModel):
    id: int | str
    building_height: float
