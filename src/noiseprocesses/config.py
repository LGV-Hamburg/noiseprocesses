from logging import getLogger

from pydantic_settings import BaseSettings

logger = getLogger(__name__)


class AppConfig(BaseSettings):
    NP_JAVA_LIB_DIR: str | None = None
    NP_LOG_LEVEL: str = "INFO"
    NP_JAVA_MAX_HEAP_SIZE: int = 4096  # Maximum heap size for the JVM
    NP_JAVA_INITIAL_HEAP_SIZE: int = 1024  # Initial heap size for the JVM
    NP_DATABASE_IN_MEMORY: bool = False  # Use in-memory database

    def print_settings(self):
        logger.info(f"Current {self.__class__.__name__} settings:")
        logger.info(vars(self))


config = AppConfig()

config.print_settings()
