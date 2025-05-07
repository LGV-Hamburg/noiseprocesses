import math
from typing import Any

from shapely.geometry import Point

from noiseprocesses.core.java_bridge import JavaBridge

java_bridge = JavaBridge.get_instance()

class Coordinate:
    """A class to represent a 3D coordinate, mimicking the Java Coordinate object."""
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z

    def distance3D(self, other: 'Coordinate') -> float:
        """Calculate the 3D distance to another coordinate."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def distance(self, other: 'Coordinate') -> float:
        """Calculate the 2D distance to another coordinate."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2
        )

def split_line_to_points(geometry, delta):
    """
    Splits a LineString or MultiLineString into points at regular intervals.

    Args:
        geometry: The input geometry (LineString or MultiLineString).
        delta: The distance between points.

    Returns:
        List[Point]: A list of points along the geometry.
    """

    points = []
    if isinstance(geometry, java_bridge.LineString):
        points.extend(split_line_string(geometry, delta))
    elif isinstance(geometry, java_bridge.MultiLineString):
        for index in range(geometry.getNumGeometries()):
            line = geometry.getGeometryN(index)
            points.extend(split_line_string(line, delta))
    return points


def split_line_string(geom, segment_size_constraint):
    """
    Splits a LineString into points at regular intervals, preserving the functionality
    of the Groovy script's splitLineStringIntoPoints function.

    Args:
        geom: A Shapely LineString geometry.
        segment_size_constraint: The maximum distance between points.

    Returns:
        List[Point]: A list of Shapely Point objects.
    """
    points = []
    geom_length = geom.getLength()  # Use JTS's getLength() method

    # Handle short geometries
    if geom_length < segment_size_constraint:
        coords = geom.getCoordinates()  # Use JTS's getCoordinates() method
        segment_length = 0
        target_segment_size = geom_length / 2.0
        for i in range(len(coords) - 1):
            point_a: Any = coords[i]
            point_b: Any = coords[i + 1]
            length = point_a.distance3D(point_b)  # Use JTS's distance3D() method
            if length + segment_length > target_segment_size:
                segment_length_fraction = (
                    target_segment_size - segment_length
                ) / length
                mid_point = Coordinate(
                    point_a.x + segment_length_fraction * (point_b.x - point_a.x),
                    point_a.y + segment_length_fraction * (point_b.y - point_a.y),
                    point_a.z + segment_length_fraction * (point_b.z - point_a.z),
                )
                points.append(Point(mid_point.x, mid_point.y, mid_point.z))
                break
            segment_length += length
        return points

    # Handle longer geometries
    target_segment_size = geom_length / math.ceil(geom_length / segment_size_constraint)
    coords = geom.getCoordinates()
    segment_length = 0.0
    mid_point = None

    for i in range(len(coords) - 1):
        point_a = coords[i]
        point_b = coords[i + 1]

        length = point_a.distance3D(point_b)

        # fall back to 2d distance
        if math.isnan(length):
            length = point_a.distance(point_b)

        while length + segment_length > target_segment_size:
            segment_length_fraction = (target_segment_size - segment_length) / length
            split_point = Coordinate(
                point_a.x + segment_length_fraction * (point_b.x - point_a.x),
                point_a.y + segment_length_fraction * (point_b.y - point_a.y),
                point_a.z + segment_length_fraction * (point_b.z - point_a.z),
            )
            if mid_point is None and (
                (length + segment_length) > (target_segment_size / 2)
            ):
                segment_length_fraction = (
                    target_segment_size / 2.0 - segment_length
                ) / length
                mid_point = (
                    point_a.x + segment_length_fraction * (point_b.x - point_a.x),
                    point_a.y + segment_length_fraction * (point_b.y - point_a.y),
                    point_a.z + segment_length_fraction * (point_b.z - point_a.z),
                )
            points.append(Point(split_point.x, split_point.y, split_point.z))
            point_a = split_point
            length = point_a.distance3D(point_b)
            segment_length = 0
            mid_point = None

        if mid_point is None and length + segment_length > target_segment_size / 2:
            segment_length_fraction = (
                target_segment_size / 2.0 - segment_length
            ) / length
            mid_point = (
                point_a.x + segment_length_fraction * (point_b.x - point_a.x),
                point_a.y + segment_length_fraction * (point_b.y - point_a.y),
                point_a.z + segment_length_fraction * (point_b.z - point_a.z),
            )
        segment_length += length

    if mid_point is not None:
        points.append(Point(mid_point))

    return points
