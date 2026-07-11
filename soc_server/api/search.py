from flask import Blueprint, jsonify, request

from services.search_service import global_search


search_api_bp = Blueprint("search_api", __name__)


@search_api_bp.get("")
def index():
    """Return grouped global search results."""

    query = request.args.get("q", "")
    return jsonify({"query": query, "results": global_search(query)}), 200
