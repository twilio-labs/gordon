import os


# Configuration settings for the Flask app created for this service
class Config:
    LOG_LEVEL = os.environ.get("GORDON_LOG_LEVEL", "INFO")
    # Should be loaded from secrets

    # Only ever set for mocks/tests
    DEBUG = False
    TESTING = False


class LocalDevelopmentConfig(Config):
    LOG_LEVEL = os.environ.get("GORDON_LOG_LEVEL", "DEBUG")
    DEBUG = os.environ.get("GORDON_DEBUG", "true") == "true"


class TestConfig(Config):
    ACTIVE_DIRECTORY_ADAPTER = "mock"
    TESTING = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


config_map = {
    'localdev': LocalDevelopmentConfig,
    'test': TestConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
