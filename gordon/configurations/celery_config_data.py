import os

# Configuration settings used for initiating the celery-redis connection
name = os.environ.get("CELERY_NAME", "gordon")
broker_host = os.environ.get("CELERY_BROKER_HOST", "gordon-redis")
broker_port = os.environ.get("CELERY_BROKER_PORT", "6379")
broker_db = os.environ.get("CELERY_BROKER_DATABASE", "1")
broker = "redis://" + broker_host + ":" + broker_port + "/" + broker_db
backend = broker
celery_config = {
    "name": name,
    "broker": broker,
    "backend": backend
}
