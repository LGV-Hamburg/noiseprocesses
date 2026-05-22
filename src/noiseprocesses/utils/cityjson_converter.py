"""
Convert a CityJSON document to a GeoJSON FeatureCollection of buildings.

Parsing, schema validation, and integer-compression transform decompression
are delegated to the ``cjio`` package (https://github.com/cityjson/cjio).
The semantic extraction (footprint + height) is custom domain logic that
``cjio`` does not provide:

Extraction strategy
-------------------
For each CityObject whose type is "Building" or "BuildingPart":

1. **Height** – taken from the first truthy attribute among
   ``measuredHeight``, ``h_dach``, ``height``; otherwise derived from the
   Z-range of all geometry vertices.
2. **Footprint** – the geometry with the *lowest* LoD value is preferred.
   * ``Solid``: the face whose exterior ring has the minimum average Z is
     used as the 2-D footprint (floor face of a LoD1 block model).
   * ``MultiSurface`` / ``CompositeSurface``: same rule applied to
     individual surfaces.
   * ``MultiSolid``: the first solid is treated as a ``Solid``.
3. The exterior ring is oriented counterclockwise (GeoJSON requirement)
   using Shapely, and closed (first == last vertex) before output.
"""

import logging

from cjio import cityjson as cjio_cityjson
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

logger = logging.getLogger(__name__)

_BUILDING_TYPES: frozenset[str] = frozenset({"Building", "BuildingPart"})
_SURFACE_GEOM_TYPES: frozenset[str] = frozenset(
    {"Solid", "MultiSurface", "CompositeSurface", "MultiSolid"}
)


# ---------------------------------------------------------------------------
# Internal helpers (operate on already-decompressed world-coordinate vertices)
# ---------------------------------------------------------------------------


def _lod_sort_key(geom: dict) -> float:
    """Return a numeric sort key for LoD (lower → preferred for footprint)."""
    lod = geom.get("lod")
    if lod is None:
        return 999.0
    try:
        return float(lod)
    except (ValueError, TypeError):
        return 999.0


def _ring_coords(
    ring: list[int],
    vertices: list[list[float]],
) -> list[tuple[float, float, float]]:
    """Resolve vertex indices to world coordinates for one ring."""
    return [(vertices[i][0], vertices[i][1], vertices[i][2]) for i in ring]


def _best_face(
    faces: list[list[list[int]]],
    vertices: list[list[float]],
) -> tuple[list[tuple[float, float]], list[float]] | None:
    """
    Among a list of faces (each face = list of rings, first ring = exterior),
    return the (2-D coords of exterior ring, all Z values) of the face whose
    exterior ring has the minimum average Z.
    """
    min_avg_z = float("inf")
    best_ring_2d: list[tuple[float, float]] | None = None
    all_z: list[float] = []

    for face in faces:
        if not face:
            continue
        exterior_indices = face[0]  # first ring is exterior
        coords_3d = _ring_coords(exterior_indices, vertices)
        z_vals = [c[2] for c in coords_3d]
        all_z.extend(z_vals)
        avg_z = sum(z_vals) / len(z_vals)
        if avg_z < min_avg_z:
            min_avg_z = avg_z
            best_ring_2d = [(c[0], c[1]) for c in coords_3d]

    if best_ring_2d is None:
        return None
    return best_ring_2d, all_z


def _footprint_solid(
    boundaries: list,
    vertices: list[list[float]],
) -> tuple[list[tuple[float, float]], float] | None:
    """Extract (2-D ring, height) from a Solid boundaries structure."""
    if not boundaries:
        return None
    exterior_shell: list[list[list[int]]] = boundaries[0]
    result = _best_face(exterior_shell, vertices)
    if result is None:
        return None
    ring_2d, all_z = result
    height = max(all_z) - min(all_z) if len(all_z) >= 2 else 0.0
    return ring_2d, height


def _footprint_multisurface(
    boundaries: list,
    vertices: list[list[float]],
) -> tuple[list[tuple[float, float]], float] | None:
    """Extract (2-D ring, height) from a MultiSurface / CompositeSurface boundaries."""
    if not boundaries:
        return None
    surfaces: list[list[list[int]]] = boundaries
    result = _best_face(surfaces, vertices)
    if result is None:
        return None
    ring_2d, all_z = result
    height = max(all_z) - min(all_z) if len(all_z) >= 2 else 0.0
    return ring_2d, height


def _extract_footprint_height(
    city_object: dict,
    vertices: list[list[float]],
) -> tuple[list[list[float]], float] | None:
    """
    Return (closed GeoJSON ring, height_m) for a building CityObject, or None
    if extraction fails.
    """
    attrs = city_object.get("attributes") or {}
    attr_height: float | None = (
        attrs.get("measuredHeight") or attrs.get("h_dach") or attrs.get("height")
    )
    if attr_height is not None:
        try:
            attr_height = float(attr_height)
        except (TypeError, ValueError):
            attr_height = None

    for geom in sorted(city_object.get("geometry", []), key=_lod_sort_key):
        geom_type = geom.get("type")
        boundaries = geom.get("boundaries", [])
        if geom_type not in _SURFACE_GEOM_TYPES:
            continue

        result: tuple[list[tuple[float, float]], float] | None = None

        if geom_type == "Solid":
            result = _footprint_solid(boundaries, vertices)
        elif geom_type in ("MultiSurface", "CompositeSurface"):
            result = _footprint_multisurface(boundaries, vertices)
        elif geom_type == "MultiSolid" and boundaries:
            result = _footprint_solid(boundaries[0], vertices)

        if result is None:
            continue

        ring_2d, geom_height = result
        height = attr_height if attr_height is not None else geom_height

        # Close the ring (GeoJSON requires first == last).
        if ring_2d and ring_2d[0] != ring_2d[-1]:
            ring_2d.append(ring_2d[0])

        # Ensure counterclockwise orientation (GeoJSON exterior ring convention).
        ring: list[list[float]] = [[c[0], c[1]] for c in ring_2d]
        try:
            poly = Polygon(ring)
            if poly.is_valid and not poly.is_empty:
                oriented = orient(poly, sign=1.0)  # sign=1 → CCW
                ring = [list(coord) for coord in oriented.exterior.coords]
        except Exception:
            pass  # use ring as-is if Shapely fails

        return ring, height

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cityjson_to_buildings_feature_collection(data: dict) -> dict:
    """
    Convert a raw CityJSON dict to a GeoJSON FeatureCollection of buildings.

    ``cjio`` is used for parsing, spec validation, and transform decompression.
    Each ``Building`` / ``BuildingPart`` city object becomes a GeoJSON Feature
    with a 2-D ``Polygon`` geometry and ``building_height`` / ``id``
    properties compatible with
    :class:`~noiseprocesses.models.building_properties.BuildingsFeatureCollection`.

    Parameters
    ----------
    data:
        Raw dict parsed from a CityJSON document.

    Raises
    ------
    ValueError
        If ``data`` is not valid CityJSON, or no valid buildings can be
        extracted.
    """
    try:
        cm = cjio_cityjson.CityJSON(j=data)
    except Exception as exc:
        raise ValueError(f"Invalid CityJSON input: {exc}") from exc

    _SUPPORTED_VERSIONS = {"1.0", "1.1", "2.0"}
    version = getattr(cm, "version", None) or data.get("version", "")
    if str(version) not in _SUPPORTED_VERSIONS:
        raise ValueError(
            f"Unsupported CityJSON version '{version}'. "
            f"Supported versions are: {sorted(_SUPPORTED_VERSIONS)}. "
            "CityJSON 0.x is not supported."
        )

    # Apply integer-compression transform (scale + translate) if present.
    # After decompress(), cm.vertices contains world-coordinate floats.
    if cm.is_transform:
        cm.decompress()

    vertices: list[list[float]] = cm.j["vertices"]
    features: list[dict] = []

    for obj_id, city_object in cm.j["CityObjects"].items():
        if city_object.get("type") not in _BUILDING_TYPES:
            continue

        result = _extract_footprint_height(city_object, vertices)
        if result is None:
            logger.warning(
                "Could not extract footprint/height for CityObject '%s'; skipping.",
                obj_id,
            )
            continue

        ring, height = result

        if height <= 0:
            logger.warning(
                "CityObject '%s' has non-positive height (%.3f); skipping.",
                obj_id,
                height,
            )
            continue

        features.append(
            {
                "type": "Feature",
                "id": obj_id,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring],
                },
                "properties": {
                    "id": obj_id,
                    "building_height": height,
                },
            }
        )

    if not features:
        raise ValueError(
            "No valid buildings could be extracted from the CityJSON input. "
            "Check that the document contains CityObjects of type 'Building' or "
            "'BuildingPart' with supported geometry types (Solid, MultiSurface)."
        )

    logger.info("Extracted %d building(s) from CityJSON input.", len(features))
    return {"type": "FeatureCollection", "features": features}
