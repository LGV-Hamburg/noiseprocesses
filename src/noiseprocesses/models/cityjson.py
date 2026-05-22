"""
Pydantic models for CityJSON input (https://www.cityjson.org).

Only the fields relevant for building footprint and height extraction are modelled.
The `boundaries` field uses `list[Any]` because its nesting depth varies by geometry
type (Solid vs MultiSurface) and is validated procedurally in the converter.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class CityJSONTransform(BaseModel):
    """Optional integer-compression transform applied to all vertices."""

    scale: list[float]
    translate: list[float]


class CityJSONGeometry(BaseModel):
    """A single geometry entry for a CityJSON city object."""

    type: str  # "Solid", "MultiSurface", "CompositeSurface", "MultiSolid", …
    lod: str | int | float | None = None
    # Deeply-nested list of vertex indices; structure differs per geometry type.
    boundaries: list[Any] = Field(default_factory=list)
    semantics: dict[str, Any] | None = None
    texture: dict[str, Any] | None = None
    material: dict[str, Any] | None = None


class CityJSONCityObject(BaseModel):
    """A single city object (Building, BuildingPart, Road, …)."""

    type: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    geometry: list[CityJSONGeometry] = Field(default_factory=list)
    children: list[str] | None = None
    parents: list[str] | None = None


class CityJSONInput(BaseModel):
    """
    Top-level CityJSON document.

    Supports CityJSON spec versions 1.0, 1.1, and 2.0.
    """

    type: Literal["CityJSON"]
    version: str
    transform: CityJSONTransform | None = None
    CityObjects: dict[str, CityJSONCityObject]
    vertices: list[list[float]]
