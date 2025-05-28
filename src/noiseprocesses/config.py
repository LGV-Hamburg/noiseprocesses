from logging import getLogger

from pydantic_settings import BaseSettings

logger = getLogger(__name__)


class AppConfig(BaseSettings):
    NP_JAVA_LIB_DIR: str | None = None
    NP_LOG_LEVEL: str = "INFO"
    NP_JAVA_MAX_HEAP_SIZE: str = "4096m"  # Maximum heap size for the JVM
    NP_JAVA_INITIAL_HEAP_SIZE: str = "1024m"  # Initial heap size for the JVM

    def print_settings(self):
        logger.info(f"Current {self.__class__.__name__} settings:")
        logger.info(vars(self))


config = AppConfig()

config.print_settings()
