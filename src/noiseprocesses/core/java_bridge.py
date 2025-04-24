import logging
import threading
from pathlib import Path
from typing import Callable, Optional

import jpype
import jpype.imports
from jpype import JImplements, JOverride
from jpype.types import JFloat

from noiseprocesses.config import config

logger = logging.getLogger(__name__)


class JavaBridge:
    """Manages JVM initialization and class loading for NoiseModelling."""

    _instance: Optional["JavaBridge"] = None

    def __init__(self):
        if JavaBridge._instance is not None:
            raise RuntimeError(
                "JavaBridge is a singleton. Use JavaBridge.get_instance()"
            )

        # Get path to NoiseModelling libraries

        if config.JAVA_LIB_DIR:
            lib_dir = Path(config.JAVA_LIB_DIR).resolve()
        else:
            current_dir = Path(__file__).parent
            logger.debug(f"Current directory: {current_dir}")

            lib_dir = (current_dir.parent.parent.parent / "dist" / "lib").resolve()

        logger.debug(f"Library directory: {lib_dir}")

        # Configure and start JVM if not already running
        if not jpype.isJVMStarted():
            classpath = str(lib_dir / "*")

            logger.info(f"Starting JVM with classpath: {classpath}")

            jpype.startJVM(
                jpype.getDefaultJVMPath(),
                # Memory configuration
                "-Xmx4096m",  # Maximum heap size
                "-Xms1024m",  # Initial heap size
                # GC optimization
                "-XX:+UseG1GC",  # Use G1 garbage collector
                "-XX:MaxGCPauseMillis=200",  # Target max GC pause time
                # Database specific options
                "-Dh2.serverCachedObjects=3000",  # H2 object cache size
                "-Dh2.objectCacheMaxPerElementSize=4096",  # Max size per object
                "-Dh2.bigDecimalIsDecimal=true",  # Improved decimal handling
                # String optimization (important for GIS)
                "-XX:+OptimizeStringConcat",
                # Class path
                f"-Djava.class.path={classpath}",
                # JPype options
                convertStrings=True,  # Auto convert strings
                interrupt=True,  # Allow thread interruption
            )

        if not jpype.isJVMStarted():
            logger.error("Failed to start JVM")
        else:
            logger.info("JVM started successfully")

        # Initialize commonly used classes
        self._init_classes()

        # redirect log messages from java
        # self._redirect_java_logging()

        # Redirect Java System.out and System.err to Python
        # self.redirect_java_output()

    def _redirect_java_logging(self):
        """Redirect Java SLF4J logs to Python logging."""

        # Dynamically define the PythonLogAppender class
        # because it needs a running JVM
        @JImplements("ch.qos.logback.core.Appender")
        class PythonLogAppender:
            def __init__(self, log_method):
                self.log_method = log_method

            @JOverride
            def doAppend(self, event):
                message = event.getFormattedMessage()
                self.log_method(f"Java: {message}")

            @JOverride
            def start(self):
                pass

            @JOverride
            def stop(self):
                pass

            @JOverride
            def isStarted(self):
                return True

        # Get the root logger from SLF4J
        logger_context = jpype.JClass("org.slf4j.LoggerFactory").getILoggerFactory()
        root_logger = logger_context.getLogger("ROOT")

        # Create and attach the Python log appender
        python_appender = PythonLogAppender(logger.info)
        root_logger.addAppender(python_appender)

    def redirect_java_output(
            self,
            progress_callback: Callable[[int, str], None] | None = None
    ):
        """Redirect Java System.out and System.err to Python logging."""

        # Create piped streams for capturing output
        self.stdout_pipe = self.PipedOutputStream()
        self.stderr_pipe = self.PipedOutputStream()

        # Redirect System.out and System.err
        self.System.setOut(self.PrintStream(self.stdout_pipe, True))
        self.System.setErr(self.PrintStream(self.stderr_pipe, True))

        # Flush streams after each write
        self.System.out.flush()
        self.System.err.flush()

        # Start threads to listen to the streams
        threading.Thread(
            target=self._capture_stream,
            args=(self.stdout_pipe, logger.info, progress_callback),
            daemon=True,
        ).start()

        threading.Thread(
            target=self._capture_stream,
            args=(self.stderr_pipe, logger.error, progress_callback),
            daemon=True,
        ).start()

    def _capture_stream(
            self,
            piped_output_stream,
            log_method,
            progress_callback: Callable[[int, str], None] | None = None
    ):
        """Capture Java output stream and log it in Python."""

        # Create a reader for the piped input stream
        piped_input_stream = self.PipedInputStream(piped_output_stream)
        reader = self.BufferedReader(self.InputStreamReader(piped_input_stream))

        match_pattern: str = "[main] INFO org.noise_planet.noisemodelling.jdbc.PointNoiseMap - Begin processing of cell"

        while True:  # Outer loop to handle broken pipe errors
            try:
                # Read lines and log them
                while True:
                    line = reader.readLine()
                    if line is None:
                        break

                    log_method(f"Java: {line}")

                    # Extract progress information
                    if match_pattern in line:
                        current_cell, total_cells, progress_percentage = self.java_log_extractor(
                            line
                        )

                        # Invoke progress_callback
                        if progress_callback:
                            progress_callback(progress_percentage, f"Begin processing of cell {current_cell} / {total_cells}")
            except Exception as e:
                if "Pipe broken" in str(e):
                    logger.warning("Broken pipe detected. Attempting to resume reading...")
                    continue  # Restart the outer loop
                else:
                    logger.error(f"Error capturing Java output: {e}")
                    break  # Exit the outer loop for other exceptions
            finally:
                # Close the reader if exiting the loop
                try:
                    reader.close()
                except Exception as e:
                    logger.error(f"Error closing Java output stream: {e}")
                break  # Exit the outer loop after cleanup

    def java_log_extractor(
            self,
            log_line: str,
    ):
        # Check if the line matches the pattern for progress
        # Extract progress information
        parts = log_line.split("Begin processing of cell")[1].strip()
        cell_info = parts.split("/")
        current_cell = int(cell_info[0].strip())
        total_cells = int(cell_info[1].strip())

        # Calculate progress percentage
        # (-1 because log indicates beginning of processing)
        progress_percentage = int(((current_cell - 1) / total_cells) * 100)

        # progress perentage is already advanced by 10%
        if progress_percentage == 0:
            progress_percentage = 10 

        return current_cell, total_cells, progress_percentage

    @classmethod
    def get_instance(cls) -> "JavaBridge":
        if cls._instance is None:
            cls._instance = JavaBridge()
        return cls._instance

    @classmethod
    def shutdown(cls):
        if jpype.isJVMStarted():
            logger.info("Shutting down JVM...")
            jpype.shutdownJVM()
        cls._instance = None

    def _init_classes(self):
        """Initialize commonly used Java classes."""
        # Using JPype's import style
        from java.io import (  # type: ignore
            BufferedReader,
            File,
            InputStreamReader,
            PipedInputStream,
            PipedOutputStream,
            PrintStream,
            StringReader,
        )
        from java.lang import System  # type: ignore
        from java.sql import DriverManager, Types  # type: ignore
        from java.time import LocalDateTime  # type: ignore
        from java.util import ArrayList, HashSet, Properties  # type: ignore
        from java.util.concurrent.atomic import AtomicInteger  # type: ignore
        from org.h2gis.api import EmptyProgressVisitor  # type: ignore
        from org.h2gis.functions.factory import H2GISFunctions  # type: ignore
        from org.h2gis.functions.io.asc import AscReaderDriver  # type: ignore
        from org.h2gis.functions.io.geojson import GeoJsonDriverFunction  # type: ignore
        from org.h2gis.functions.io.utility import PRJUtil  # type: ignore
        from org.h2gis.functions.spatial.crs import (  # type: ignore
            ST_SetSRID,
            ST_Transform,
        )
        from org.h2gis.utilities import (  # type: ignore
            GeometryTableUtilities,
            JDBCUtilities,
            SpatialResultSet,
            TableLocation,
        )
        from org.h2gis.utilities.dbtypes import DBUtils  # type: ignore
        from org.h2gis.utilities.wrapper import ConnectionWrapper  # type: ignore
        from org.locationtech.jts.io import WKTReader, WKTWriter  # type: ignore
        from org.noise_planet.noisemodelling.jdbc import (  # type: ignore
            BezierContouring,
            LDENConfig,
            LDENPointNoiseMapFactory,
            LDENPropagationProcessData,
            PointNoiseMap,
            TriangleNoiseMap,
        )
        from org.noise_planet.noisemodelling.pathfinder import (  # type: ignore
            RootProgressVisitor,
        )
        from org.noise_planet.noisemodelling.pathfinder.utils import (  # type: ignore
            JVMMemoryMetric,
            PowerUtils,
            ProfilerThread,
            ProgressMetric,
            ReceiverStatsMetric,
        )
        from org.noise_planet.noisemodelling.propagation import (  # type: ignore
            PropagationProcessPathData,
        )
        # from ch.qos.logback.classic import LoggerContext  # type: ignore
        # from ch.qos.logback.classic.spi import ILoggingEvent  # type: ignore
        # from ch.qos.logback.core import AppenderBase  # type: ignore

        # Store classes as instance attributes
        # self.LoggerContext = LoggerContext
        # self.ILoggingEvent = ILoggingEvent
        # self.AppenderBase = AppenderBase

        self.AtomicInteger = AtomicInteger
        self.ArrayList = ArrayList
        self.JFloat = JFloat
        self.BezierContouring = BezierContouring
        self.File = File
        self.HashSet = HashSet
        self.LocalDateTime = LocalDateTime
        self.DBUtils = DBUtils
        self.LDENConfig = LDENConfig
        self.LDENConfig_INPUT_MODE = LDENConfig.INPUT_MODE
        self.LDENConfig_TIME_PERIOD = LDENConfig.TIME_PERIOD
        self.LDENPointNoiseMapFactory = LDENPointNoiseMapFactory
        self.LDENPropagationProcessData = LDENPropagationProcessData
        self.PropagationProcessPathData = PropagationProcessPathData
        self.PointNoiseMap = PointNoiseMap

        self.StringReader = StringReader
        self.System = System
        self.PrintStream = PrintStream
        self.PipedOutputStream = PipedOutputStream
        self.BufferedReader = BufferedReader
        self.InputStreamReader = InputStreamReader
        self.PipedInputStream = PipedInputStream

        self.TriangleNoiseMap = TriangleNoiseMap
        self.Types = Types

        self.ConnectionWrapper = ConnectionWrapper
        self.GeoJsonDriverFunction = GeoJsonDriverFunction
        self.TableLocation = TableLocation

        self.EmptyProgressVisitor = EmptyProgressVisitor
        self.PowerUtils = PowerUtils

        self.DriverManager = DriverManager
        self.H2GISFunctions = H2GISFunctions
        self.Properties = Properties

        self.GeometryTableUtilities = GeometryTableUtilities
        self.JDBCUtilities = JDBCUtilities
        self.SpatialResultSet = SpatialResultSet

        self.DriverManager = DriverManager
        self.AscReaderDriver = AscReaderDriver
        self.ST_SetSRID = ST_SetSRID
        self.ST_Transform = ST_Transform
        self.PRJUtil = PRJUtil
        self.WKTReader = WKTReader
        self.WKTWriter = WKTWriter
        self.RootProgressVisitor = RootProgressVisitor

        self.ProgressMetric = ProgressMetric
        self.ProfilerThread = ProfilerThread
        self.JVMMemoryMetric = JVMMemoryMetric
        self.ReceiverStatsMetric = ReceiverStatsMetric
