from celery import Celery
from gordon.api_server import create_app
from celery.signals import after_setup_task_logger
from pythonjsonlogger import jsonlogger
from datetime import datetime
from gordon import celery
import sys
import logging
app = create_app()

"""
Setting up the celery worker and logger format
"""
celery.conf.update(app.config)
TaskBase = celery.Task


class ContextTask(TaskBase):
    abstract = True

    def __call__(self, *args, **kwargs):
        with app.app_context():
            return TaskBase.__call__(self, *args, **kwargs)


celery.Task = ContextTask


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record,
                                                    record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('levelname'):
            log_record['levelname'] = log_record['levelname'].upper()
        else:
            log_record['levelname'] = record.levelname


@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    # for handler in logger.handlers:

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter('%(message)s %(levelname)s'
                                             ' %(timestamp)s %(module)s'
                                             ' %(lineno)s %(process)s'
                                             '%(filename)s %(funcName)s'
                                             '%(thread)s'))
    logger.addHandler(handler)


@celery.task
def example_task():
    print("celery: Web app sync")
