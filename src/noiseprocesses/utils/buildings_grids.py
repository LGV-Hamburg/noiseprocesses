import logging
from pathlib import Path
from typing import Optional

from noiseprocesses.core.database import NoiseDatabase, SQLBuilder
from noiseprocesses.models.grid_config import (
    BuildingGridConfig2d, BuildingGridConfig3d
)
from shapely.geometry import base, Polygon

logger = logging.getLogger(__name__)


class BuildingGridGenerator2d:
    """Generates a 2D grid of receivers around building facades"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.target_srid = 0

    def generate_receivers(self, config: BuildingGridConfig2d) -> str:
        """
        Generate a 2D grid of receivers around building facades.

        Args:
            config: Configuration for grid generation.

        Returns:
            str: Name of the created receivers table.
        """
        logger.info("Starting 2D building grid generation")

        # Get SRID from input tables
        self.target_srid = self._get_srid(config)

        # Drop existing tables
        self.database.execute(SQLBuilder.drop_table(config.output_table))

        # Create temporary table for receiver lines
        logger.info("Creating receiver lines")
        self.database.execute(
            f"""
            CREATE TABLE tmp_receivers_lines AS
            SELECT
                b.pk AS building_pk,
                ST_SimplifyPreserveTopology(
                    ST_ToMultiLine(ST_Buffer(b.the_geom, {config.distance_from_wall}, 'join=bevel')),
                    0.05
                ) AS the_geom
            FROM {config.buildings_table} b
            """
        )
        self.database.execute("CREATE SPATIAL INDEX ON tmp_receivers_lines(the_geom)")

        # Convert lines to points
        logger.info("Converting lines to points")
        self.database.execute(
            f"""
            CREATE TABLE {config.output_table} AS
            SELECT
                ST_SetSRID(ST_PointN(the_geom, generate_series(1, ST_NumPoints(the_geom))), {self.target_srid}) AS the_geom
            FROM tmp_receivers_lines
            """
        )
        self.database.execute(f"CREATE SPATIAL INDEX ON {config.output_table}(the_geom)")

        logger.info(f"2D building grid generation completed: {config.output_table}")
        return config.output_table

    def _get_srid(self, config: BuildingGridConfig2d) -> int:
        """Get SRID from the buildings table."""
        srid = self.database.query_scalar(
            f"SELECT ST_SRID(the_geom) FROM {config.buildings_table} LIMIT 1"
        )
        if srid in (0, 3785, 4326):
            raise ValueError(
                f"Invalid SRID: {srid}. Please use a metric projection system."
            )
        return srid


class BuildingGridGenerator3d:
    """Generates a 3D grid of receivers around building facades"""

    def __init__(self, database: NoiseDatabase):
        self.database = database
        self.target_srid = 0

    def generate_receivers(self, config: BuildingGridConfig3d) -> str:
        """
        Generate a 3D grid of receivers around building facades.

        Args:
            config: Configuration for grid generation.

        Returns:
            str: Name of the created receivers table.
        """
        logger.info("Starting 3D building grid generation")

        # Get SRID from input tables
        self.target_srid = self._get_srid(config)

        # Drop existing tables
        self.database.execute(SQLBuilder.drop_table(config.output_table))

        # Create temporary table for receiver lines
        logger.info("Creating receiver lines")
        self.database.execute(
            f"""
            CREATE TABLE tmp_receivers_lines AS
            SELECT
                b.pk AS building_pk,
                ST_SimplifyPreserveTopology(
                    ST_ToMultiLine(ST_Buffer(b.the_geom, {config.distance_from_wall}, 'join=bevel')),
                    0.05
                ) AS the_geom,
                b.height AS building_height
            FROM {config.buildings_table} b
            """
        )
        self.database.execute("CREATE SPATIAL INDEX ON tmp_receivers_lines(the_geom)")

        # Generate 3D points
        logger.info("Generating 3D points")
        self.database.execute(
            f"""
            CREATE TABLE {config.output_table} AS
            SELECT
                ST_SetSRID(
                    ST_MakePoint(
                        ST_X(the_geom),
                        ST_Y(the_geom),
                        generate_series(1.5, building_height, {config.height_between_levels})
                    ),
                    {self.target_srid}
                ) AS the_geom
            FROM tmp_receivers_lines
            """
        )
        self.database.execute(f"CREATE SPATIAL INDEX ON {config.output_table}(the_geom)")

        logger.info(f"3D building grid generation completed: {config.output_table}")
        return config.output_table

    def _get_srid(self, config: BuildingGridConfig3d) -> int:
        """Get SRID from the buildings table."""
        srid = self.database.query_scalar(
            f"SELECT ST_SRID(the_geom) FROM {config.buildings_table} LIMIT 1"
        )
        if srid in (0, 3785, 4326):
            raise ValueError(
                f"Invalid SRID: {srid}. Please use a metric projection system."
            )
        return srid