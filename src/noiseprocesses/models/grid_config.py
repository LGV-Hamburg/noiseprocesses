from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, computed_field

from shapely.geometry import base
from shapely import wkt

class GridType(str, Enum):
    """Grid generation type"""
    REGULAR = "regular"
    DELAUNAY = "delaunay"

class GridConfig(BaseModel):
    """Base configuration for grid generation"""
    
    class Config:
        """Pydantic model configuration"""
        arbitrary_types_allowed = True

    # Required parameters
    buildings_table: str = Field(
        ...,
        description="Name of the Buildings table containing THE_GEOM"
    )
    
    # Common optional parameters with defaults
    height: float = Field(
        default=4.0,
        gt=0,
        description="Height of receivers in meters"
    )
    
    output_table: str = Field(
        default="RECEIVERS",
        description="Name of the output receivers table"
    )
    
    sources_table: Optional[str] = Field(
        default=None,
        description="Table name containing source geometries"
    )
    
    fence_table: Optional[str] = Field(
        default=None,
        description="Table name to extract bounding box"
    )

    fence_wkt: Optional[str] = Field(
        default=None,
        description="Well-Known Text (WKT) string for limiting receiver extent"
    )
    
    create_triangles: bool = Field(
        default=True,
        description="Whether to create triangle meshes"
    )

    grid_type: GridType = Field(
        default=GridType.REGULAR,
        description="Type of grid to generate"
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

class RegularGridConfig(GridConfig):
    """Configuration for regular grid generation"""
    
    grid_type: GridType = Field(
        default=GridType.REGULAR,
        description="Type of grid to generate"
    )
    
    delta: float = Field(
        default=10.0,
        gt=0,
        description="Spacing between receivers in meters"
    )

class DelaunayGridConfig(GridConfig):
    """Configuration for Delaunay grid generation"""
    
    grid_type: GridType = Field(
        default=GridType.DELAUNAY,
        description="Type of grid to generate"
    )

    max_cell_dist: float = Field(
        default=600.0,
        gt=0,
        description="Maximum cell size for domain splitting (meters)"
    )
    
    road_width: float = Field(
        default=2.0,
        gt=0,
        description="Buffer around roads (meters)"
    )
    
    max_area: float = Field(
        default=2500.0,
        gt=0,
        description="Maximum triangle area (m²)"
    )
    
    iso_surface_in_buildings: bool = Field(
        default=False,
        description="Enable isosurfaces over buildings"
    )

    error_dump_folder: Optional[str] = Field(
        default=None,
        description="Folder to dump debug information on triangulation errors"
    )