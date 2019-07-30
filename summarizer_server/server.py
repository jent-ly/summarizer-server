import json
import logging
import os
import sys

from flask import Flask, abort, request
from settings import Settings
from models import database, Feedback, User
from user_service import UserService
from feedback_service import FeedbackService
from text_rank import TextRank

debug = os.environ.get("DEBUG", "false").lower() == "true"

log = logging.getLogger("summarizer_server")

app = Flask(__name__)
app.config.from_object(Settings)
database.init_app(app)

userservice = UserService()
feedbackservice = FeedbackService()
textrank = TextRank()


@app.before_first_request
def before_first_request():
    textrank.setup()


@app.route("/api/")
def index():
    return "Summarizer API"


@app.route("/api/extract", methods=["POST"])
def extract():
    # TODO: call into summary algorithm
    return "Extractive summary endpoint"


@app.route("/api/summarize", methods=["POST"])
def summarize():
    if not request.is_json:
        abort(400)
    request_payload = request.get_json()
    top_sentences = textrank.summarize(
        request_payload["html"], request_payload.get("percent_sentences")
    )
    return json.dumps(top_sentences)


@app.route("/api/feedback/submit", methods=["POST"])
def submit_feedback():
    if not request.is_json:
        abort(400)

    request_payload = request.get_json()
    url = request_payload.get("url", "")
    score = request_payload.get("score", "")

    if url == "" or score == "":
        abort(400)

    email = request_payload.get("email", "")
    gaia = request_payload.get("gaia", "")

    # check if user wishes to be anonymous
    user = userservice.get_anonymous()
    if email != "" and gaia != "":
        user = userservice.get(email)

    # create user if it does not yet exist
    if user is None:
        user = userservice.create(email, gaia)

    feedback = feedbackservice.submit(
        url, score, request_payload.get("description", ""), user.id
    )

    response = {
        "message": "Successfully submitted feedback",
        "feedback": feedbackservice.serialize_single(feedback),
        "success": True,
    }
    return json.dumps(response)


# TODO: add feedback deletion
# TODO: make certain routes internal only
@app.route("/api/feedback/view", methods=["GET"])
def view_feedback():
    # TODO: consider pagination
    all_feedback = feedbackservice.get_all()
    response = {
        "message": "Successfully got feedback",
        "feedback": feedbackservice.serialize_multiple(all_feedback),
        "success": True,
    }
    return json.dumps(response)


# TODO: add user deletion and creation
# TODO: make certain routes internal only
@app.route("/api/users/view", methods=["GET"])
def view_users():
    # TODO: consider pagination
    all_users = userservice.get_all()
    response = {
        "message": "Successfully got users",
        "users": userservice.serialize_multiple(all_users),
        "success": True,
    }
    return json.dumps(response)


def configure_logger(debug):
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG

    # Configure logger and remove default flask logging
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(log_level)

    app.logger.handlers = []
    app.logger.propagate = True


if __name__ == "__main__":
    configure_logger(debug)
    with app.app_context():
        database.create_all()
    app.run(host="0.0.0.0", debug=debug, port=int(os.environ.get("PORT", 5000)))
