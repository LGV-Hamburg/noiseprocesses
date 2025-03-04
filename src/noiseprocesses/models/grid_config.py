from typing import Optional, Union
from pydantic import BaseModel, Field, computed_field

from shapely.geometry import Polygon, MultiPolygon, base
from shapely import wkt

class RegularGridConfig(BaseModel):
    """Configuration for regular grid generation following NoiseModelling parameters"""

    class Config:
        """Pydantic model configuration"""
        arbitrary_types_allowed = True

    # Required parameters
    buildings_table: str = Field(
        ...,
        description=(
            "Name of the Buildings table containing THE_GEOM (POLYGON/MULTIPOLYGON)"
        )
    )
    
    # Optional parameters with defaults
    delta: float = Field(
        default=10.0,
        gt=0,
        description="Spacing between receivers in meters (Offset in Cartesian plane)"
    )
    
    height: float = Field(
        default=4.0,
        gt=0,
        description="Height of receivers in meters"
    )
    
    output_table: str = Field(
        default="RECEIVERS",
        description="Name of the output receivers table"
    )
    
    # Optional parameters
    sources_table: Optional[str] = Field(
        default=None,
        description="Table name containing source geometries to keep receivers 1m away from"
    )
    
    fence_table: Optional[str] = Field(
        default=None,
        description="Table name to extract bounding box for limiting receiver extent"
    )

    fence_wkt: Optional[str] = Field(
        default=None,
        description="Well-Known Text (WKT) string for limiting receiver extent"
    )
    
    create_triangles: bool = Field(
        default=False,
        description="Whether to create triangle meshes from receivers"
    )

    @computed_field
    @property
    def fence_geometry(self) -> Optional[base.BaseGeometry]:
        """Computed field that converts WKT to Geometry"""
        if self.fence_wkt is None:
            return None
        try:
            return wkt.loads(self.fence_wkt)
        except Exception as e:
            raise ValueError(f"Invalid WKT string: {str(e)}")
