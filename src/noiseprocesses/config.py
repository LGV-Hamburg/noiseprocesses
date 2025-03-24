from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    JAVA_LIB_DIR: str | None = None

config = AppConfig()
