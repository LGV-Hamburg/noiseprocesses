from geojson_pydantic import Feature, Polygon
from pydantic import BaseModel


class BboxProperties(BaseModel):
    pass


class BboxFeature(Feature[Polygon, BboxProperties]):
    """A GeoJSON Feature representing a polygon with bounding box properties."""

    pass
