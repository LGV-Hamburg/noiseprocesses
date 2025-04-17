from geojson_pydantic import Feature, Polygon
from pydantic import BaseModel

class BboxProperties(BaseModel):
    pass

class BboxFeature(Feature[Polygon, BboxProperties]):
    """A GeoJSON Feature representing a polygon with bounding box properties."""
    pass

if __name__ == "__main__":
    # Example usage
    print(BboxFeature.model_json_schema())