import os
from pathlib import Path
from osgeo import gdal
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Configure GDAL
gdal.UseExceptions()  # Enable exceptions for better error handling

# Set PROJ data path
VENV_PATH = Path(os.environ.get('VIRTUAL_ENV', '.venv'))
PROJ_DIR = VENV_PATH / 'share' / 'proj'
if not PROJ_DIR.exists():
    PROJ_DIR.mkdir(parents=True)
os.environ['PROJ_LIB'] = str(PROJ_DIR)


@dataclass
class ASCData:
    """Container for ASC raster data and metadata."""
    data: np.ndarray
    ncols: int
    nrows: int
    xllcorner: float
    yllcorner: float
    cellsize: float
    nodata_value: float

    def dump_to_asc(self, output_path: str) -> None:
        """Write data to ASC file.
        
        Args:
            output_path: Path to output ASC file
            
        Example:
            >>> dem_data = convert_to_asc_array('dem.tif')
            >>> dem_data.dump_to_asc('output.asc')
        """
        # Write header first
        header = (
            f"ncols {self.ncols}\n"
            f"nrows {self.nrows}\n"
            f"xllcorner {self.xllcorner}\n"
            f"yllcorner {self.yllcorner}\n"
            f"cellsize {self.cellsize}\n"
            f"NODATA_value {self.nodata_value}\n"
        )
        
        # Save data with header
        np.savetxt(
            output_path,
            self.data,
            fmt='%.3f',
            delimiter=' ',
            header=header,
            comments=''
        )
        
        logger.info(f"Successfully wrote ASC data to {output_path}")

def convert_to_asc_array(input_path: str) -> ASCData:
    """Convert GeoTIFF to in-memory ASC format.
    
    Args:
        input_path: Local file path or HTTPS URL to (CO)GeoTIFF
        
    Returns:
        ASCData object containing the raster data and metadata
    """
    try:
        # Handle HTTPS URLs
        if input_path.startswith('https://'):
            input_path = f'/vsicurl/{input_path}'
            
        # Open the input raster
        src_ds: gdal.Dataset = gdal.Open(input_path)

        if not src_ds:
            raise ValueError(f"Could not open {input_path}")
        
        # Read data into numpy array directly from source
        data = src_ds.GetRasterBand(1).ReadAsArray()

        # Get metadata
        gt = src_ds.GetGeoTransform()
        xllcorner = gt[0]
        yllcorner = gt[3] + gt[5] * src_ds.RasterYSize
        cellsize = gt[1]
        nodata_value = src_ds.GetRasterBand(1).GetNoDataValue()

        
        # Create ASC data container
        asc_data = ASCData(
            data=data,
            ncols=src_ds.RasterXSize,
            nrows=src_ds.RasterYSize,
            xllcorner=xllcorner,
            yllcorner=yllcorner,
            cellsize=cellsize,
            nodata_value=nodata_value if nodata_value else -9999
        )
        
        logger.info(f"Successfully converted {input_path} to in-memory ASC format")
        return asc_data
        
    except Exception as e:
        logger.error(f"Failed to convert raster: {e}")
        raise