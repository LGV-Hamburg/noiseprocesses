# This code is entirely based on https://github.com/Universite-Gustave-Eiffel/NoiseModelling/tree/main/wps_scripts/src/main/groovy/org/noise_planet/noisemodelling/wps/Receivers/Building_Grid.groovy
# from DECIDE team from the Lab-STICC (CNRS) and by the Mixt Research Unit in Environmental Acoustics (Université Gustave Eiffel)
import math
from typing import Any

from shapely.geometry import Point

from noiseprocesses.core.java_bridge import JavaBridge


class Coordinate:
    """A class to represent a 3D coordinate, mimicking the Java Coordinate object."""

    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z

    def distance3D(self, other: "Coordinate") -> float:
        """Calculate the 3D distance to another coordinate."""
        return math.sqrt(
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        )

    def distance(self, other: "Coordinate") -> float:
        """Calculate the 2D distance to another coordinate."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


def split_line_to_points(geometry, delta):
    """
    Splits a LineString or MultiLineString into points at regular intervals.

    Args:
        geometry: The input geometry (LineString or MultiLineString).
        delta: The distance between points.

    Returns:
        List[Point]: A list of points along the geometry.
    """
    java_bridge = JavaBridge.get_instance()

    points = []
    if isinstance(geometry, java_bridge.LineString):
        points.extend(split_line_string_simple(geometry, delta))
    elif isinstance(geometry, java_bridge.MultiLineString):
        for index in range(geometry.getNumGeometries()):
            line = geometry.getGeometryN(index)
            points.extend(split_line_string_simple(line, delta))
    return points


def split_line_string(geom, max_point_spacing ):
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
    geom_length = geom.getLength()  # Total length of the input line

    # If the geometry is shorter than the constraint, just place a midpoint
    if geom_length < max_point_spacing :
        coordinates = geom.getCoordinates()
        accumulated_length = 0
        actual_segment_length = geom_length / 2.0  # Place midpoint
        for i in range(len(coordinates) - 1):
            start_coord: Any = coordinates[i]
            next_coord: Any = coordinates[i + 1]
            segment_length = start_coord.distance3D(next_coord)
            # Fallback to 2D if 3D distance is not available
            if math.isnan(segment_length):
                segment_length = start_coord.distance(next_coord)
            # If we've reached the midpoint, calculate and add it
            if segment_length + accumulated_length > actual_segment_length:
                segment_length_fraction = (
                    actual_segment_length - accumulated_length
                ) / segment_length
                mid_point = Coordinate(
                    start_coord.x + segment_length_fraction * (next_coord.x - start_coord.x),
                    start_coord.y + segment_length_fraction * (next_coord.y - start_coord.y),
                    start_coord.z + segment_length_fraction * (next_coord.z - start_coord.z),
                )
                points.append(Point(mid_point.x, mid_point.y, mid_point.z))
                break  # Only one midpoint needed for short lines
            accumulated_length += segment_length
        return points

    # For longer geometries, split into segments as close as possible to the constraint
    # Calculate the actual segment size so that all segments are nearly equal and <= constraint
    actual_segment_length = geom_length / math.ceil(geom_length / max_point_spacing )
    coordinates = geom.getCoordinates()
    accumulated_length = 0.0  # Tracks distance along the current segment
    mid_point = None  # Will hold the midpoint if needed

    # Iterate over each segment between coordinates
    for i in range(len(coordinates) - 1):
        start_coord = coordinates[i]
        next_coord = coordinates[i + 1]

        # Calculate 3D segment length, fallback to 2D if needed
        segment_length = start_coord.distance3D(next_coord)
        if math.isnan(segment_length):
            segment_length = start_coord.distance(next_coord)

        # Place points at every actual_segment_length interval within this segment
        while segment_length + accumulated_length > actual_segment_length:
            # Compute where along the segment the next point should be
            segment_length_fraction = (actual_segment_length - accumulated_length) / segment_length
            split_point = Coordinate(
                start_coord.x + segment_length_fraction * (next_coord.x - start_coord.x),
                start_coord.y + segment_length_fraction * (next_coord.y - start_coord.y),
                start_coord.z + segment_length_fraction * (next_coord.z - start_coord.z),
            )
            # Optionally, compute and store the midpoint for later use
            if mid_point is None and (
                (segment_length + accumulated_length) > (actual_segment_length / 2)
            ):
                segment_length_fraction = (
                    actual_segment_length / 2.0 - accumulated_length
                ) / segment_length
                mid_point = (
                    start_coord.x + segment_length_fraction * (next_coord.x - start_coord.x),
                    start_coord.y + segment_length_fraction * (next_coord.y - start_coord.y),
                    start_coord.z + segment_length_fraction * (next_coord.z - start_coord.z),
                )
            # Add the split point to the result
            points.append(Point(split_point.x, split_point.y, split_point.z))

            # Move point_a to the new split point and recalculate remaining length
            start_coord = split_point
            segment_length = start_coord.distance3D(next_coord)
            if math.isnan(segment_length):
                segment_length = start_coord.distance(next_coord)

            accumulated_length = 0  # Reset for next segment
            mid_point = None

        # If midpoint hasn't been set, check if we should set it now
        if mid_point is None and segment_length + accumulated_length > actual_segment_length / 2:
            segment_length_fraction = (
                actual_segment_length / 2.0 - accumulated_length
            ) / segment_length
            mid_point = (
                start_coord.x + segment_length_fraction * (next_coord.x - start_coord.x),
                start_coord.y + segment_length_fraction * (next_coord.y - start_coord.y),
                start_coord.z + segment_length_fraction * (next_coord.z - start_coord.z),
            )

        accumulated_length += segment_length  # Accumulate distance for next iteration

    # If a midpoint was found, add it to the result
    if mid_point is not None:
        points.append(Point(mid_point))

    return points

def split_line_string_simple(geom, max_point_spacing):
    java_bridge = JavaBridge.get_instance()

    LengthIndexedLine = java_bridge.LengthIndexedLine
    length_indexed_line = LengthIndexedLine(geom)

    geom_length = geom.getLength()
    distance = 0.0
    points = []
    while distance < geom_length:
        pt = length_indexed_line.extractPoint(distance)
        # pt is a Coordinate, so use pt.x, pt.y, pt.z
        points.append(Point(pt.x, pt.y, getattr(pt, 'z', 0.0)))
        distance += max_point_spacing
    # Optionally add the endpoint
    pt_end = length_indexed_line.extractPoint(geom_length)
    points.append(Point(pt_end.x, pt_end.y, getattr(pt_end, 'z', 0.0)))

    return points