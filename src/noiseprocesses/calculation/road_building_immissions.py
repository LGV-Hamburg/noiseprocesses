import copy
import json
import logging
from collections import defaultdict
from typing import Callable

from pydantic import HttpUrl

from noiseprocesses.calculation.road_propagation import RoadPropagationCalculator
from noiseprocesses.core.database import NoiseDatabase
from noiseprocesses.core.java_bridge import JavaBridge
from noiseprocesses.models.grid_config import BuildingGridConfig, GridType
from noiseprocesses.models.internal import (
    BuildingsFeatureCollectionInternal,
    GroundAbsorptionFeatureCollectionInternal,
    RoadsFeatureCollectionInternal,
)
from noiseprocesses.models.noise_calculation_config import (
    NoiseCalculationConfig,
    NoiseCalculationUserInput,
    OutputDayTimeSoundLevels,
)
from noiseprocesses.utils.buildings_grids import (
    BuildingGridGenerator2d,
    BuildingGridGenerator3d,
)
from noiseprocesses.utils.dem import load_convert_save_dem

logger = logging.getLogger(__name__)


class ImmissionsAroundBuildingsCalculator:
    """Main class handling the complete noise calculation process"""

    def __init__(self, config: NoiseCalculationConfig | None = None):
        self.config = config or NoiseCalculationConfig()  # defaults

        self.database = NoiseDatabase(
            db_file=self.config.database.name, in_memory=self.config.database.in_memory
        )
        # match output control and table names:
        self.match_oct = {
            "noise_day": "LDAY_GEOM",
            "noise_evening": "LEVENING_GEOM",
            "noise_night": "LNIGHT_GEOM",
            "noise_den": "LDEN_GEOM",
        }

    def _join_by_stack_id(self, feature_collection: dict) -> dict:
        grouped = defaultdict(list)
        for feature in feature_collection["features"]:
            stack_id = feature["properties"]["STACK_ID"]
            grouped[stack_id].append(feature)

        joined_features = []
        for stack_id, features in grouped.items():
            # Use the geometry of the first feature (all have same x/y)
            base_feature = copy.deepcopy(features[0])
            base_feature["properties"] = {"STACK_ID": stack_id}
            
            # Remove z from geometry coordinates
            coords = base_feature["geometry"]["coordinates"]
            if len(coords) == 3:
                base_feature["geometry"]["coordinates"] = coords[:2]
            
            for f in features:
                z = f["geometry"]["coordinates"][2]
                laeq = f["properties"]["LAEQ"]
                base_feature["properties"][f"laeq_level_{z}"] = laeq
            
            joined_features.append(base_feature)

        return {"type": "FeatureCollection", "features": joined_features}

    def _ensure_roads_have_z(self, roads_table: str, default_z: float = 0.05) -> None:
        """Ensure that roads have Z-values by updating 2D geometries to 3D.

        Args:
            roads_table (str): Name of the roads table.
            default_z (float): Default Z-value to add to 2D geometries.
        """
        logger.info(f"Ensuring roads in table '{roads_table}' have Z-values")

        # Check if the geometries are 2D
        dimension_query = f"""
            SELECT ST_CoordDim(THE_GEOM) AS dimension
            FROM {roads_table}
            LIMIT 1;
        """
        dimension_result = self.database.query(dimension_query)

        if dimension_result and dimension_result[0][0] == 2:
            logger.info(
                f"Roads in table '{roads_table}' are 2D."
                f"Adding Z-values with default Z={default_z}."
            )
            # Update geometries to 3D with the default Z-value
            # copy, as in-place update did not work
            copy_query = f"""
                DROP TABLE IF EXISTS ROADS_TRAFFIC_3D;
                CREATE TABLE ROADS_TRAFFIC_3D AS 
                SELECT 
                ST_Force3D(THE_GEOM) AS THE_GEOM,
                -- List all other columns here
                PK, LV_D, LV_E, LV_N, MV_D, MV_E, MV_N, 
                HGV_D, HGV_E, HGV_N, WAV_D, WAV_E, WAV_N, 
                WBV_D, WBV_E, WBV_N, LV_SPD_D, LV_SPD_E, LV_SPD_N, 
                MV_SPD_D, MV_SPD_E, MV_SPD_N, HGV_SPD_D, HGV_SPD_E, HGV_SPD_N, 
                WAV_SPD_D, WAV_SPD_E, WAV_SPD_N, WBV_SPD_D, WBV_SPD_E, WBV_SPD_N, 
                PVMT, TEMP_D, TEMP_E, TEMP_N, TS_STUD, PM_STUD, 
                JUNC_DIST, JUNC_TYPE, SLOPE
                FROM {roads_table};
            """

            self.database.execute(copy_query)

            # add primary key
            add_pk_query = """
                ALTER TABLE ROADS_TRAFFIC_3D ALTER COLUMN PK SET NOT NULL;
                ALTER TABLE ROADS_TRAFFIC_3D ADD PRIMARY KEY (PK);
            """
            self.database.execute(add_pk_query)

            # update geometry metadata
            update_metadata_query = """
                ALTER TABLE ROADS_TRAFFIC_3D 
                ADD CONSTRAINT enforce_srid_the_geom CHECK (ST_SRID(THE_GEOM) = 25832);
            """
            self.database.execute(update_metadata_query)

            rename_query = f"""
                -- Rename the old table (backup)
                DROP TABLE IF EXISTS ROADS_TRAFFIC_OLD;
                ALTER TABLE ROADS_TRAFFIC RENAME TO ROADS_TRAFFIC_OLD;

                -- Rename the new table to the original name
                ALTER TABLE ROADS_TRAFFIC_3D RENAME TO {roads_table};
            """
            self.database.execute(rename_query)

        else:
            logger.info(f"Roads in table '{roads_table}' already have Z-values.")

    def calculate_noise_levels(
        self,
        user_input: NoiseCalculationUserInput,
        user_output: dict[OutputDayTimeSoundLevels, dict],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict:
        """
        Calculate complete noise levels including emission and propagation

        Args:
            user_input (NoiseCalculationUserInput): User input for noise calculation
            user_output (dict[OutputIsoSurfaces, dict]): User output for noise calculation

        Returns:
            dict: Noise Isosurfaces for user selected outputs
        """
        # initialize redirecting java output
        java_bridge = JavaBridge.get_instance()

        java_bridge.redirect_java_output(progress_callback=progress_callback)

        # config setup, take defaults if user did not provide any
        self.config.acoustic_params = (
            user_input.acoustic_parameters or self.config.acoustic_params
        )
        self.config.propagation_settings = (
            user_input.propagation_settings or self.config.propagation_settings
        )
        self.config.output_controls = user_output or self.config.output_controls

        self.config.building_grid_settings = (
            user_input.building_grid_settings or self.config.building_grid_settings
        )

        # validate user inputs
        # - buildings user input -> buildings internal
        if progress_callback:
            progress_callback(1, "Validating user input")

        buildings = BuildingsFeatureCollectionInternal.from_user_collection(
            user_input.buildings
        )
        # - roads user input -> roads internal
        roads_traffic = RoadsFeatureCollectionInternal.from_user_collection(
            user_input.roads
        )
        # - grounds
        grounds = None
        if user_input.ground_absorption:
            grounds = GroundAbsorptionFeatureCollectionInternal.from_user_collection(
                user_input.ground_absorption
            )

        # - dem
        dem_url = user_input.dem_url
        dem_bbox_feature = user_input.dem_bbox_feature

        if dem_bbox_feature and not dem_url:
            raise ValueError(
                "If 'dem_bbox_feature' was provided, 'dem_url' must be provided, too."
            )

        if progress_callback:
            progress_callback(2, "Loading DEM data")

        dem_path = None
        if dem_url:
            dem_path = load_convert_save_dem(dem_url)

        # setup the database
        noise_db = NoiseDatabase(
            self.config.database.name, self.config.database.in_memory
        )

        if progress_callback:
            progress_callback(3, "Importing into database")

        # convert crs
        crs: int = 0
        if isinstance(user_input.crs, HttpUrl) and user_input.crs.path:
            crs = int(user_input.crs.path.split("/")[-1])

        # import data
        # - buildings -> geojson import
        noise_db.import_geojson(
            buildings.model_dump(exclude_none=True),  # omit empty fields like bbox
            self.config.required_input.building_table,
            crs,
        )

        # - roads -> geojson import
        noise_db.import_geojson(
            roads_traffic.model_dump(exclude_unset=True),  # omit empty fields like bbox
            self.config.required_input.roads_table,
            crs,
        )

        # make the roads 3D, set height to 0.05
        # Ensure roads have Z-values
        self._ensure_roads_have_z(self.config.required_input.roads_table)

        # - load dem -> tif
        if dem_path:
            noise_db.import_raster(
                dem_path,
                self.config.optional_input.dem_table,
                int(crs),
            )

        # - grounds -> geojson
        if grounds:
            noise_db.import_geojson(
                grounds.model_dump(exclude_none=True),
                self.config.optional_input.ground_absorption_table,
                crs,
            )

        if progress_callback:
            progress_callback(
                4, "Importing into database complete. Generating receivers grid."
            )

        # generate receivers near building facades
        # - check if user provided building grid settings
        if not user_input.building_grid_settings:
            raise ValueError(
                "Building grid settings are required for calculating "
                "emissions on building facades."
            )
        # - translate user input to config
        # - default: 2D
        grid_generator = BuildingGridGenerator2d(noise_db)

        grid_config = BuildingGridConfig(
            buildings_table=self.config.required_input.building_table,
            receivers_table_name=self.config.required_input.receivers_table,
            sources_table_name=self.config.required_input.roads_table,
            distance_from_wall=user_input.building_grid_settings.distance_from_wall,
            receiver_distance=user_input.building_grid_settings.receiver_distance,
            receiver_height=user_input.building_grid_settings.receiver_height_2d,
        )

        has_stack_id = False

        if user_input.building_grid_settings.grid_type == GridType.BUILDINGS_3D:
            grid_generator = BuildingGridGenerator3d(noise_db)
            has_stack_id = True

        grid_generator.generate_receivers(grid_config)

        if progress_callback:
            progress_callback(
                10, "Receivers around buildings generated. Calculating noise levels..."
            )

        # calculate propagation
        road_prop = RoadPropagationCalculator(noise_db)
        road_prop.calculate_propagation(
            self.config,
            True if dem_url else False,
            True if grounds else False,
            has_stack_id,
        )

        if progress_callback:
            progress_callback(
                90, "Calculating noise levels complete. Generating isocontours"
            )

        # finally: export the results

        output: dict[str, dict] = {}

        for output_table, output_control in self.config.output_controls.items():
            table_name = self.match_oct[output_table]

            # export to dict/geojson/FeatureCollection
            # H2 DB has no support for in-memory data export
            surface_file = noise_db.export_data(table_name)

            # read the data...
            # replace path with actual data
            with open(surface_file, "r") as stream:
                output[output_table] = json.load(stream)

                if (
                    has_stack_id
                    and
                    user_input.building_grid_settings.join_receivers_by_xy_location_3d
                ):
                    logger.info(
                        "Joining features by xy location "
                        f"into one point for '{output_table}'"
                    )
                    output[output_table] = self._join_by_stack_id(output[output_table])

        if progress_callback:
            progress_callback(100, "Calculating noise levels complete.")
        # ...and return it
        return output
