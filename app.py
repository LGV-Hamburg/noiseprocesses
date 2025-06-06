import logging
from typing import Any, Callable, Dict

import uvicorn
from fastprocesses.api.server import OGCProcessesAPI
from fastprocesses.core.base_process import BaseProcess
from fastprocesses.core.models import (
    ProcessDescription,
    ProcessInput,
    ProcessJobControlOptions,
    ProcessOutput,
    ProcessOutputTransmission,
    Schema,
)
from fastprocesses.processes.process_registry import register_process
from pydantic import ValidationError

from noiseprocesses.calculation.road_building_immissions import (
    ImmissionsAroundBuildingsCalculator
)
from noiseprocesses.calculation.road_noise import RoadNoiseModellingCalculator
from noiseprocesses.models.noise_calculation_config import (
    NoiseCalculationConfig,
    NoiseCalculationUserInput,
)
from noiseprocesses.models.output import NoiseCalculationOutput

logger = logging.getLogger(__name__)


@register_process("traffic_noise_propagation")
class TrafficNoiseProp(BaseProcess):
    async def execute(
        self,
        exec_body: Dict[str, Any],
        job_progress_callback: Callable[[int, str], None] | None = None,
    ) -> NoiseCalculationOutput:
        user_outputs = exec_body["outputs"]

        if job_progress_callback:
            job_progress_callback(0, f"Beginning calculations for {user_outputs}")

        calculator = RoadNoiseModellingCalculator(
            noise_calculation_config=NoiseCalculationConfig()
        )
        try:
            user_input: NoiseCalculationUserInput = (
                NoiseCalculationUserInput.model_validate(exec_body["inputs"])
            )
        except ValidationError as validation_error:
            logger.error("Some inputs are not valid: %s", validation_error)
            if job_progress_callback:
                job_progress_callback(
                    0,
                    "Calculations failed. "
                    f"Reason: Invalid inputs ({validation_error}).",
                )

            raise ValueError(
                validation_error.errors(
                    include_input=False, include_url=False, include_context=False
                )
            )
        except ValueError as value_error:
            logger.error("Some inputs are not valid: %s", value_error)
            if job_progress_callback:
                job_progress_callback(
                    0, f"Calculations failed. Reason: Invalid inputs ({value_error})."
                )

            raise value_error

        result_raw = calculator.calculate_noise_levels(
            user_input, user_outputs, job_progress_callback
        )

        result = NoiseCalculationOutput.model_validate(result_raw)

        if job_progress_callback:
            job_progress_callback(100, f"Done calculating {user_outputs}!")

        return result

    # Define process description as a class variable
    process_description = ProcessDescription(
        id="traffic_noise_propagation",
        title="Traffic Noise Propagation Calculation",
        version="v4.0.5-1.0.2",
        description=(
            "A process for calculating traffic noise "
            "propagation and creating isosurfaces based on NoiseModelling 4.0.5"
            "(https://noise-planet.org/noisemodelling.html)"
        ),
        jobControlOptions=[
            ProcessJobControlOptions.ASYNC_EXECUTE,
        ],
        outputTransmission=[ProcessOutputTransmission.VALUE],
        inputs={
            "buildings": ProcessInput(
                title="Buildings Feature Collection",
                description="A GeoJSON FeatureCollection representing buildings",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                        {
                            "$ref": "https://raw.githubusercontent.com/LGV-Hamburg/noiseprocesses/refs/heads/main/schemas/buildings-schema.json"
                        },
                    ]
                ),
                minOccurs=1,
                maxOccurs=1,
            ),
            "roads": ProcessInput(
                title="Roads Feature Collection",
                description="A GeoJSON FeatureCollection representing roads",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                        {
                            "$ref": "https://raw.githubusercontent.com/LGV-Hamburg/noiseprocesses/refs/heads/main/schemas/roads-schema.json"
                        },
                    ]
                ),
                minOccurs=1,
                maxOccurs=1,
            ),
            "crs": ProcessInput(
                title="Coordinate Reference System",
                description=(
                    "Coordinate reference system (CRS) of the input data in "
                    "the form of: 'http://www.opengis.net/def/crs/EPSG/0/25832', "
                    "or as EPSG integer code."
                ),
                schema=Schema(type="string"),
                minOccurs=1,
                maxOccurs=1,
            ),
            "dem_url": ProcessInput(
                title="Digital Elevation Model",
                description=(
                    "A URL to the Digital Elevation Model."
                    "The URL must point to a COG file and"
                    "must have abounding box. If the bbox"
                    "is omitted polygon feature can be submitted instead."
                ),
                schema=Schema(type="string", format="uri"),
                minOccurs=0,
                maxOccurs=1,
            ),
            "dem_bbox_feature": ProcessInput(
                title="Polygon feature as substitute for a bbox",
                description=(
                    "A GeoJSON Polygon feature representing the bounding box for the DEM."
                    "This is used if the dem_url does not contain a bbox."
                ),
                minOccurs=0,
                maxOccurs=1,
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature"},
                        {"$ref": "https://geojson.org/schema/Polygon.json"},
                    ]
                ),
            ),
            "ground_absorption": ProcessInput(
                title="Ground Absorption Feature Collection",
                description="A GeoJSON FeatureCollection representing ground absorption",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                        {
                            "$ref": "https://raw.githubusercontent.com/LGV-Hamburg/noiseprocesses/refs/heads/main/schemas/grounds-schema.json"
                        },
                    ]
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "acoustic_parameters": ProcessInput(
                title="Acoustic Parameters",
                description="Parameters for acoustic calculations",
                schema=Schema(
                    type="object",
                    properties={
                        "wall_alpha": Schema.model_validate({
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.1,
                        }),
                        "max_source_distance": Schema.model_validate({
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1000.0,
                            "default": 150.0,
                        }),
                        "max_reflection_distance": Schema.model_validate({
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1000.0,
                            "default": 50.0,
                        }),
                        "reflection_order": Schema.model_validate({
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 2,
                            "default": 1,
                        }),
                        "humidity": Schema.model_validate({
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 100.0,
                            "default": 70.0,
                        }),
                        "temperature": Schema.model_validate({
                            "type": "number",
                            "minimum": -20.0,
                            "maximum": 50.0,
                            "default": 15.0,
                        }),
                    },
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "propagation_settings": ProcessInput(
                title="Propagation Settings",
                description="Settings for noise propagation",
                schema=Schema(
                    type="object",
                    required=["vertical_diffraction", "horizontal_diffraction", "favorable_day"],
                    properties={
                        "vertical_diffraction": Schema.model_validate(
                            {"type": "boolean", "default": False}
                        ),
                        "horizontal_diffraction": Schema.model_validate(
                            {"type": "boolean", "default": True}
                        ),
                        "favorable_day": Schema.model_validate({
                            "type": "string",
                            "default": "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5",
                        }),
                        "favorable_evening": Schema.model_validate({
                            "default": None,
                            "oneOf": [
                                {"type": "string"},
                                {"type": "null"}
                            ]
                        }),
                        "favorable_night": Schema.model_validate({
                            "default": None,
                            "oneOf": [
                                {"type": "string"},
                                {"type": "null"}
                            ]
                        }),
                    },
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "receiver_grid_settings": ProcessInput(
                title="Receiver Grid Settings",
                description="Settings for the receiver grid",
                schema=Schema.model_validate({
                    "type": "object",
                    "properties": {
                        "grid_type": {
                            "type": "string",
                            "enum": ["DELAUNAY"],
                            "default": "DELAUNAY",
                        },
                        "calculation_height": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100.0,
                            "default": 4.0,
                        },
                        "max_area": {
                            "type": "number",
                            "minimum": 0,
                            "default": 2500.0,
                            "maximum": 2500.0,
                        },
                        "max_cell_dist": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 10000.0,
                            "default": 600.0,
                        },
                        "road_width": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 50.0,
                            "default": 2.0,
                        },
                    },
                }),
                minOccurs=0,
                maxOccurs=1,
            ),
            "isosurface_settings": ProcessInput(
                title="IsoSurface Settings",
                description="Settings for isosurface generation",
                schema=Schema.model_validate({
                    "type": "object",
                    "properties": {
                        "iso_classes": {
                            "type": "string",
                            "default": (
                                "35.0,40.0,45.0,50.0,55.0,60.0,65.0,70.0,75.0,80.0,200.0"
                            ),
                        },
                        "smooth_coefficient": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 100.0,
                            "default": 0.5,
                        },
                    },
                }),
                minOccurs=0,
                maxOccurs=1,
            ),
        },
        outputs={
            "noise_day": ProcessOutput(
                title="Noise isosurface day",
                description="Isosurface containing noise levels during the day period (6-18h)",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_evening": ProcessOutput(
                title="Noise isosurface evening",
                description="Isosurface containing noise levels during the evening period (18-22h)",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_night": ProcessOutput(
                title="Noise isosurface night",
                description="Isosurface containing noise levels during the night period (22-6h)",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_den": ProcessOutput(
                title="Noise isosurface day-evening-night",
                description="Isosurface containing noise levels during the a 24 hour period",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
        },
        keywords=["text", "processing"],
        metadata={
            "created": "2025-02-19",
            "updated": "2025-04-24",
            "provider": "Agency for Geoinformation and Surveying Hamburg",
        },
    )


@register_process("traffic_noise_buildings")
class TrafficNoiseBuildings(BaseProcess):
    async def execute(
        self,
        exec_body: Dict[str, Any],
        job_progress_callback: Callable[[int, str], None] | None = None,
    ) -> NoiseCalculationOutput:
        user_outputs = exec_body["outputs"]

        if job_progress_callback:
            job_progress_callback(0, f"Beginning calculations for {user_outputs}")

        calculator = ImmissionsAroundBuildingsCalculator(
            config=NoiseCalculationConfig()
        )
        try:
            user_input: NoiseCalculationUserInput = (
                NoiseCalculationUserInput.model_validate(exec_body["inputs"])
            )
        except ValidationError as validation_error:
            logger.error("Some inputs are not valid: %s", validation_error)
            if job_progress_callback:
                job_progress_callback(
                    0,
                    f"Calculations failed. Reason: Invalid inputs ({validation_error}).",
                )

            raise ValueError(validation_error.errors())
        except ValueError as value_error:
            logger.error("Some inputs are not valid: %s", value_error)
            if job_progress_callback:
                job_progress_callback(
                    0, f"Calculations failed. Reason: Invalid inputs ({value_error})."
                )

            raise value_error

        result_raw = calculator.calculate_noise_levels(
            user_input, user_outputs, job_progress_callback
        )

        result = NoiseCalculationOutput.model_validate(result_raw)

        if job_progress_callback:
            job_progress_callback(100, f"Done calculating {user_outputs}!")

        return result

    # Define process description as a class variable
    process_description = ProcessDescription(
        id="traffic_noise_buildings",
        title="Traffic Noise Immission Calculation around building facades",
        version="v4.0.5-1.1.0",
        description=(
            "A process for calculating traffic noise "
            "immission near buildings based on NoiseModelling 4.0.5 "
            "(https://noise-planet.org/noisemodelling.html) "
            "for one level (building_grid_settings.BUILDINGS_2D) "
            "or multiple levels (building_grid_settings.BUILDINGS_3D)."
        ),
        jobControlOptions=[
            ProcessJobControlOptions.ASYNC_EXECUTE,
        ],
        outputTransmission=[ProcessOutputTransmission.VALUE],
        inputs={
            "buildings": ProcessInput(
                title="Buildings Feature Collection",
                description="A GeoJSON FeatureCollection representing buildings",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                        {
                            "$ref": "https://raw.githubusercontent.com/LGV-Hamburg/noiseprocesses/refs/heads/main/schemas/buildings-schema.json"
                        },
                    ]
                ),
                minOccurs=1,
                maxOccurs=1,
            ),
            "roads": ProcessInput(
                title="Roads Feature Collection",
                description="A GeoJSON FeatureCollection representing roads",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                        {
                            "$ref": "https://raw.githubusercontent.com/LGV-Hamburg/noiseprocesses/refs/heads/main/schemas/roads-schema.json"
                        },
                    ]
                ),
                minOccurs=1,
                maxOccurs=1,
            ),
            "crs": ProcessInput(
                title="Coordinate Reference System",
                description=(
                    "Coordinate reference system (CRS) of the input data in "
                    "the form of: 'http://www.opengis.net/def/crs/EPSG/0/25832', "
                    "or as EPSG integer code."
                ),
                schema=Schema(type="string"),
                minOccurs=1,
                maxOccurs=1,
            ),
            "dem_url": ProcessInput(
                title="Digital Elevation Model",
                description=(
                    "A URL to the Digital Elevation Model."
                    "The URL must point to a COG file and"
                    "must have abounding box. If the bbox"
                    "is omitted polygon feature can be submitted instead."
                ),
                schema=Schema(type="string", format="uri"),
                minOccurs=0,
                maxOccurs=1,
            ),
            "dem_bbox_feature": ProcessInput(
                title="Polygon feature as substitute for a bbox",
                description=(
                    "A GeoJSON Polygon feature representing the bounding box for the DEM."
                    "This is used if the dem_url does not contain a bbox."
                ),
                minOccurs=0,
                maxOccurs=1,
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature"},
                        {"$ref": "https://geojson.org/schema/Polygon.json"},
                    ]
                ),
            ),
            "ground_absorption": ProcessInput(
                title="Ground Absorption Feature Collection",
                description="A GeoJSON FeatureCollection representing ground absorption",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                        {
                            "$ref": "https://raw.githubusercontent.com/LGV-Hamburg/noiseprocesses/refs/heads/main/schemas/grounds-schema.json"
                        },
                    ]
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "acoustic_parameters": ProcessInput(
                title="Acoustic Parameters",
                description="Parameters for acoustic calculations",
                schema=Schema.model_validate({
                    "type": "object",
                    "properties": {
                        "wall_alpha": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.1,
                        },
                        "max_source_distance": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1000.0,
                            "default": 150.0,
                        },
                        "max_reflection_distance": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1000.0,
                            "default": 50.0,
                        },
                        "reflection_order": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 2,
                            "default": 1,
                        },
                        "humidity": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 100.0,
                            "default": 70.0,
                        },
                        "temperature": {
                            "type": "number",
                            "minimum": -20.0,
                            "maximum": 50.0,
                            "default": 15.0,
                        },
                    },
                }),
                minOccurs=0,
                maxOccurs=1,
            ),
            "propagation_settings": ProcessInput(
                title="Propagation Settings",
                description="Settings for noise propagation",
                schema=Schema.model_validate({
                    "type": "object",
                    "required": ["vertical_diffraction", "horizontal_diffraction", "favorable_day"],
                    "properties": {
                        "vertical_diffraction": {"type": "boolean", "default": False},
                        "horizontal_diffraction": {"type": "boolean", "default": True},
                        "favorable_day": {
                            "type": "string",
                            "default": "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5",
                        },
                        "favorable_evening": Schema.model_validate({
                            "default": None,
                            "oneOf": [
                                {"type": "string"},
                                {"type": "null"}
                            ]
                        }),
                        "favorable_night": Schema.model_validate({
                            "default": None,
                            "oneOf": [
                                {"type": "string"},
                                {"type": "null"}
                            ]
                        }),
                    },
                }),
                minOccurs=0,
                maxOccurs=1,
            ),
            "building_grid_settings": ProcessInput(
                title="Receiver Grid Settings",
                description="Settings for the receiver grid",
                schema=Schema.model_validate({
                    "type": "object",
                    "properties": {
                        "grid_type": {
                            "type": "string",
                            "enum": ["BUILDINGS_2D", "BUILDINGS_3D"],
                            "default": "BUILDINGS_2D",
                        },
                        "receiver_height_2d": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100.0,
                            "default": 4.0,
                        },
                        "receiver_distance": {
                            "type": "number",
                            "minimum": 1,
                            "maximum": 1000.0,
                            "default": 10.0,
                        },
                        "distance_from_wall": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 50.0,
                            "default": 2.0,
                        },
                        "height_between_levels_3d": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100.0,
                            "default": 4.0,
                        },
                        "join_receivers_by_xy_location_3d": {
                            "type": "boolean",
                            "default": True,
                        },
                    },
                }),
                minOccurs=1,
                maxOccurs=1,
            ),
        },
        outputs={
            "noise_day": ProcessOutput(
                title="Noise day",
                description="Point locations with Laeq around buildings during the day period (6-18h)",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_evening": ProcessOutput(
                title="Noise evening",
                description="Point locations with Laeq around buildings during the evening period (18-22h)",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_night": ProcessOutput(
                title="Noise night",
                description="Point locations with Laeq around buildings during the night period (22-6h)",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_den": ProcessOutput(
                title="Noise day-evening-night",
                description="Point locations with Laeq around buildings during the a 24 hour period",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
        },
        keywords=["text", "processing"],
        metadata={
            "created": "2025-05-08",
            "updated": "2025-05-08",
            "provider": "Agency for Geoinformation and Surveying Hamburg",
        },
    )


# Create the FastAPI app
app = OGCProcessesAPI(
    contact={
        "name": "Agency for Geoinformation and Surveying Hamburg",
        "url": "https://www.hamburg.de/politik-und-verwaltung/behoerden/behoerde-fuer-stadtentwicklung-und-wohnen/aemter-und-landesbetrieb/landesbetrieb-geoinformation-und-vermessung",
        "email": "info@gv.hamburg.de"
    },
    license={
        "name": "GNU General Public License v3.0",
        "url": "https://github.com/LGV-Hamburg/noiseprocesses/blob/main/LICENSE",
    },
    terms_of_service=""
).get_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        log_level=None,
    )
