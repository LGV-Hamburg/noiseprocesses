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

from noiseprocesses.calculation.road_noise import RoadNoiseModellingCalculator
from noiseprocesses.models.noise_calculation_config import (
    NoiseCalculationConfig,
    NoiseCalculationUserInput,
)

logger = logging.getLogger(__name__)


@register_process("traffic_noise_propagation")
class TrafficNoiseProcess(BaseProcess):
    async def execute(
        self, exec_body: Dict[str, Any],
        progress_callback: Callable[[int, str], None] | None = None
    ) -> Dict[str, Any]:
        
        if progress_callback:
            progress_callback(1, "Processing input")

        calculator = RoadNoiseModellingCalculator(
            noise_calculation_config=NoiseCalculationConfig()
        )
        try:
            user_input: NoiseCalculationUserInput = (
                NoiseCalculationUserInput.model_validate(exec_body["inputs"])
            )
        except ValueError as value_error:
            logger.error("Some inputs are not valid: %s", value_error)
        
        user_outputs = exec_body["outputs"]

        result = calculator.calculate_noise_levels(
            user_input, user_outputs
        )

        if progress_callback:
            progress_callback(100, f"Done calculating {user_outputs}!")

        return result

    # Define process description as a class variable
    process_description = ProcessDescription(
        id="traffic_noise_propagation",
        title="Traffic Noise Propagation Calculation",
        version="1.0.0",
        description=(
            "A process for calculating traffic noise "
            "propagation and creating isosurfaces"
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
                        {"$ref": "https://bitbucket.org/geowerkstatt-hamburg/noiseprocesses/schema/buildings-schema.json"},
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
                        {"$ref": "https://bitbucket.org/geowerkstatt-hamburg/noiseprocesses/schema/buildings-schema.json"},
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
            "dem": ProcessInput(
                title="Digital Elevation Model",
                description="A URL to the Digital Elevation Model",
                schema=Schema(type="string", format="uri"),
                minOccurs=0,
                maxOccurs=1,
            ),
            "ground_absorption": ProcessInput(
                title="Ground Absorption Feature Collection",
                description="A GeoJSON FeatureCollection representing ground absorption",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
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
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "propagation_settings": ProcessInput(
                title="Propagation Settings",
                description="Settings for noise propagation",
                schema=Schema(
                    type="object",
                    properties={
                        "vertical_diffraction": {"type": "boolean", "default": False},
                        "horizontal_diffraction": {"type": "boolean", "default": False},
                        "favorable_day": {
                            "type": "string",
                            "default": "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5",
                        },
                        "favorable_evening": {"type": "string", "default": None},
                        "favorable_night": {"type": "string", "default": None},
                    },
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "receiver_grid_settings": ProcessInput(
                title="Receiver Grid Settings",
                description="Settings for the receiver grid",
                schema=Schema(
                    type="object",
                    properties={
                        "grid_type": {
                            "type": "string",
                            "enum": ["REGULAR", "DELAUNAY", "BUILDINGS"],
                            "default": "DELAUNAY",
                        },
                        "calculation_height": {
                            "type": "number",
                            "minimum": 0,
                            "default": 4.0,
                        },
                        "max_area": {"type": "number", "minimum": 0, "default": 2500.0},
                        "max_cell_dist": {
                            "type": "number",
                            "minimum": 0,
                            "default": 600.0,
                        },
                        "road_width": {"type": "number", "minimum": 0, "default": 2.0},
                    },
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
            "iosurface_settings": ProcessInput(
                title="IsoSurface Settings",
                description="Settings for isosurface generation",
                schema=Schema(
                    type="object",
                    properties={
                        "iso_classes": {
                            "type": "string",
                            "default": "35.0,40.0,45.0,50.0,55.0,60.0,65.0,70.0,75.0,80.0,200.0",
                        },
                        "smooth_coefficient": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 100.0,
                            "default": 0.5,
                        },
                    },
                ),
                minOccurs=0,
                maxOccurs=1,
            ),
        },
        outputs={
            "noise_day": ProcessOutput(
                title="Output Text",
                description="Processed text",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_evening": ProcessOutput(
                title="Output Text",
                description="Processed text",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_night": ProcessOutput(
                title="Output Text",
                description="Processed text",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
            "noise_den": ProcessOutput(
                title="Output Text",
                description="Processed text",
                schema=Schema(
                    allOf=[
                        {"format": "geojson-feature-collection"},
                        {"$ref": "https://geojson.org/schema/FeatureCollection.json"},
                    ]
                ),
            ),
        },
        keywords=["text", "processing"],
        metadata={"created": "2024-02-19", "provider": "Example Organization"},
    )


# Create the FastAPI app
app = OGCProcessesAPI(
    title="Noise Processes API",
    version="0.1.0",
    description="Calculate traffic noise propagation and create isosurfaces",
).get_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        log_level=None,
    )
