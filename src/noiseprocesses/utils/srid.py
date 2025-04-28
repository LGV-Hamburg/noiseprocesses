from noiseprocesses.core.java_bridge import JavaBridge
from noiseprocesses.core.database import NoiseDatabase


def get_srid(database: NoiseDatabase, java_bridge: JavaBridge, config) -> int:
    """
    Get SRID from input tables using JavaBridge's GeometryTableUtilities.

    Args:
        database: The NoiseDatabase instance.
        java_bridge: The JavaBridge instance.
        config: Configuration object containing table names.

    Returns:
        int: The SRID of the input tables.

    Raises:
        ValueError: If no valid SRID is found or if the SRID is invalid.
    """
    srid = 0
    TableLocation = java_bridge.TableLocation

    # Try buildings table first
    if hasattr(config, "buildings_table") and config.buildings_table:
        srid = java_bridge.GeometryTableUtilities.getSRID(
            database.connection, TableLocation.parse(config.buildings_table)
        )

    # Try sources table if no SRID found
    if srid == 0 and hasattr(config, "sources_table") and config.sources_table:
        srid = java_bridge.GeometryTableUtilities.getSRID(
            database.connection, TableLocation.parse(config.sources_table)
        )

    # Try fence table if no SRID found
    if srid == 0 and hasattr(config, "fence_table") and config.fence_table:
        srid = java_bridge.GeometryTableUtilities.getSRID(
            database.connection, TableLocation.parse(config.fence_table)
        )

    if srid in (0, 3785, 4326):
        raise ValueError(
            f"Invalid SRID: {srid}. Please use a metric projection system."
        )

    return srid