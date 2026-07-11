from flask import Blueprint


alerts_api_bp = Blueprint("alerts_api", __name__)

# Alert APIs should wait until detection and alert lifecycle rules exist.
