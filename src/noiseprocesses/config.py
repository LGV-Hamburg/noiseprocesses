from pydantic_settings import BaseSettings
from logging import getLogger

logger = getLogger(__name__)

class AppConfig(BaseSettings):
    JAVA_LIB_DIR: str | None = None
    LOG_LEVEL: str = "INFO"
    JAVA_MAX_HEAP_SIZE: str = "4096m"  # Maximum heap size for the JVM
    JAVA_INITIAL_HEAP_SIZE: str = "1024m"  # Initial heap size for the JVM

    def print_settings(self):
        logger.info(
            "Current %s settings:",
            self.__class__.__name__
        )
        logger.info(vars(self))

config = AppConfig()

config.print_settings()