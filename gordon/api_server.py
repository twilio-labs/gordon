from flask import Flask
from gordon.configurations.api_server_config_data import config_map
from celery.utils.log import get_task_logger
import os
logger = get_task_logger(__name__)


# Setting up the Flask app to receive requests on
def create_app(config_object_name=None,
               config_dict=None,
               **kwargs):
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    if config_object_name is None:
        config_object_name = os.environ.get("GORDON_CONFIG", "default")
    app.config.from_object(config_map.get(config_object_name))

    if config_dict is not None:
        app.config.from_mapping(config_dict)

    from gordon.blueprints.blueprints import api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    return app
