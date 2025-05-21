from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field
from shapely import wkt
from shapely.geometry import base


class GridType(StrEnum):
    """Grid generation type"""

    REGULAR = "regular".upper()
    DELAUNAY = "delaunay".upper()
    BUILDINGS_2D = "buildings_2d".upper()
    BUILDINGS_3D = "buildings_3d".upper()


class GridSettingsUser(BaseModel):
    grid_type: GridType = Field(default=GridType.DELAUNAY)
    calculation_height: float = Field(
        default=4.0, gt=0, description="Height of receivers in meters"
    )
    max_area: float = Field(
        default=2500.0, gt=0, description="Maximum triangle area (m²)"
    )
    max_cell_dist: float = Field(
        default=600.0,
        gt=0,
        description="Maximum cell size for domain splitting (meters)",
    )
    road_width: float = Field(
        default=2.0, gt=0, description="Buffer around roads (meters)"
    )


class BuildingGridSettingsUser(BaseModel):
    """Configuration for building grid generation"""

    grid_type: Literal[GridType.BUILDINGS_2D, GridType.BUILDINGS_3D] = Field(
        default=GridType.BUILDINGS_2D,
        description="Type of grid to generate",
    )

    receiver_height_2d: float = Field(
        default=4.0, gt=0,
        description="Height of receivers in meters"
    )
    distance_from_wall: float = Field(
        default=2.0, description="Distance of receivers from the wall (meters)", gt=0
    )  # Distance of receivers from the wall (meters)
    height_between_levels_3d: float | None = Field(
        default=None, description="Height between levels for 3D building grids", gt=0
    )  # Height between levels 3D grids
    receiver_distance: float = Field(
        default=10.0,
        gt=0,
        description="Spacing between receivers (meters)",
    )  # Spacing between receivers (meters)


class GridConfig(BaseModel):
    """Base configuration for grid generation"""

    class Config:
        """Pydantic model configuration"""

        arbitrary_types_allowed = True

    # Required parameters
    buildings_table: str = Field(
        ..., description="Name of the Buildings table containing THE_GEOM"
    )

    # Common optional parameters with defaults
    height: float = Field(
        default=4.0,
        alias="calculation_height",
        gt=0,
        description="Height of receivers in meters",
    )

    output_table: str = Field(
        default="RECEIVERS", description="Name of the output receivers table"
    )

    sources_table: Optional[str] = Field(
        default=None, description="Table name containing source geometries"
    )

    fence_table: Optional[str] = Field(
        default=None, description="Table name to extract bounding box"
    )

    fence_wkt: Optional[str] = Field(
        default=None,
        description="Well-Known Text (WKT) string for limiting receiver extent",
    )

    create_triangles: bool = Field(
        default=True, description="Whether to create triangle meshes"
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
        default=GridType.REGULAR, description="Type of grid to generate"
    )

    delta: float = Field(
        default=10.0, gt=0, description="Spacing between receivers in meters"
    )


class DelaunayGridConfig(GridConfig):
    """Configuration for Delaunay grid generation"""

    grid_type: GridType = Field(
        default=GridType.DELAUNAY, description="Type of grid to generate"
    )

    max_cell_dist: float = Field(
        default=600.0,
        gt=0,
        description="Maximum cell size for domain splitting (meters)",
    )

    road_width: float = Field(
        default=2.0, gt=0, description="Buffer around roads (meters)"
    )

    max_area: float = Field(
        default=2500.0, gt=0, description="Maximum triangle area (m²)"
    )

    iso_surface_in_buildings: bool = Field(
        default=False, description="Enable isosurfaces over buildings"
    )

    error_dump_folder: Optional[str] = Field(
        default=None,
        description="Folder to dump debug information on triangulation errors",
    )


class BuildingGridConfig(BaseModel):
    """Base configuration for building grid generation"""

    class Config:
        """Pydantic model configuration"""

        arbitrary_types_allowed = True
        populate_by_name = True

    grid_type: Literal[GridType.BUILDINGS_2D, GridType.BUILDINGS_3D] = Field(
        default=GridType.BUILDINGS_2D, description="Type of grid to generate"
    )

    receiver_height: float = Field(
        default=10.0, gt=0, description="Spacing between receivers (meters)"
    )  # Spacing between receivers (meters)

    # Required parameters
    buildings_table: str = Field(
        default="BUILDINGS",
        description="Name of the Buildings table containing THE_GEOM",
    )

    # Common optional parameters with defaults
    receivers_table_name: str = Field(
        default="RECEIVERS_BUILDINGS", description="Name of the output receivers table"
    )

    sources_table_name: Optional[str] = Field(
        default=None, description="Table name containing source geometries"
    )

    distance_from_wall: float = Field(
        default=2.0,
        description="Distance of receivers from the wall (meters)",
    )  # Distance of receivers from the wall (meters)
    
    receiver_distance: float = Field(
        default=10.0, gt=0, description="Spacing between receivers in meters"
    )

    height_between_levels: float = Field(
        default=2.5,
        gt=0,
        description="Height between levels for 3D building grids",
    )  # Height between levels 3D grids
