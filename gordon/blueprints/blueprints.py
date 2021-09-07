from flask import Blueprint
from flask import request, jsonify
from . import api_exceptions
from gordon.services.common.logger import get_logger
from gordon.services.github.sender_verification import SenderVerificationProcessor
from gordon.services.celery_worker.webhook_async_processor import webhook_async

import json
import requests

logger = get_logger()
api_blueprint = Blueprint('api_blueprint', __name__)


@api_blueprint.errorhandler(api_exceptions.APIException)
def handleAPIException(error):
    response = error.jsonify()
    response.status_code = error.code
    return response


# Call to initiate a async celery task to process the received payload
def handle_webhook(webhook_json, payload_event):
    # call webhook processor in a celery worker file
    webhook_async.delay(webhook_json, payload_event)


# Health check endpoint to see if the API server is up and running
@api_blueprint.route('/healthcheck', methods=['GET'])
def healthcheck():
    return json.dumps({"healthcheck": "ready"})


# Route to be used in your Github app to receive the payload events and process the about.yaml file
@api_blueprint.route('/validate-aboutyaml', methods=['POST'])
def webhook_handler():
    event_type = request.headers.get('X-GitHub-Event')
    sent_signature = request.headers.get('X-Hub-Signature')

    request_body = request.get_data()
    webhook_payload = json.loads(request_body)
    """
    call SenderVerificationProcessor to process the payload and ensure it's in a consumable format and all the info
    needed to run the status check is present in the PR payload
    """
    sender_verify = SenderVerificationProcessor(event_type, sent_signature, request_body)
    sender_check, payload_event = sender_verify.verify_sender()

    if not sender_check:
        raise api_exceptions.BadRequestException("Invalid Sender")

    """
    call checks api if sender verification passes
    create task to get diff, load plugins, and scan PR
    """
    try:
        handle_webhook(webhook_payload, payload_event)
    except Exception as e:
        logger.error(f"Failed queing celery task: {e}")

    return jsonify({
        "Status": 200
    })
