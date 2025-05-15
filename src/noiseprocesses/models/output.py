from pydantic import BaseModel
from geojson_pydantic import FeatureCollection

class NoiseCalculationOutput(BaseModel):
    noise_den: FeatureCollection | None = None
    noise_day: FeatureCollection | None = None
    noise_evening: FeatureCollection | None = None
    noise_night: FeatureCollection | None = None
