import tempfile
from pydantic import AnyUrl
import httpx
from noiseprocesses.models.dem_feature import BboxFeature
from noiseprocesses.utils.raster import convert_to_asc_array

def load_convert_save_dem(
        dem_url: AnyUrl,
        feature_bbox: BboxFeature | None = None,
):
    """
    Download a GeoTIFF from a URL, convert it to ASC format, and save it to a temporary file.

    Args:
        user_input: An object with a `dem_url` attribute containing the GeoTIFF URL.

    Returns:
        str: Path to the temporary ASC file.
    """

    # Download the GeoTIFF file using httpx
    with httpx.Client() as client:
        with client.stream("GET", str(dem_url)) as response:
            response.raise_for_status()  # Raise an error for HTTP issues
            with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as temp_tif:
                for chunk in response.iter_bytes():
                    temp_tif.write(chunk)
                temp_tif_path = temp_tif.name

    # Convert the GeoTIFF to ASC format
    asc_data = convert_to_asc_array(temp_tif_path)

    # Create a temporary file to store the ASC data
    with tempfile.NamedTemporaryFile(suffix=".asc", delete=False) as temp_asc:
        asc_file_path = temp_asc.name
        asc_data.dump_to_asc(asc_file_path)

    return asc_file_path