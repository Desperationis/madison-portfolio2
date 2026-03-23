"""Flask Blueprint with all /api/* endpoints for the portfolio manager."""

import logging
import traceback

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from gui import config_ops, file_ops, git_ops
from gui.file_ops import IMAGE_EXTS

api = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@api.before_request
def require_json_for_mutations():
    """Require JSON content type for all POST/PUT requests (except multipart uploads)."""
    if request.method in ("POST", "PUT"):
        if request.endpoint == "api.upload_images":
            return None
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
    return None


# --- Error handlers ---


@api.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request errors."""
    return jsonify({"error": str(e.description) if isinstance(e, HTTPException) else str(e)}), 400


@api.errorhandler(404)
def not_found(e):
    """Handle 404 Not Found errors."""
    return jsonify({"error": str(e.description) if isinstance(e, HTTPException) else str(e)}), 404


@api.errorhandler(RequestEntityTooLarge)
def request_too_large(e):
    """Handle 413 Request Entity Too Large."""
    return jsonify({"error": "File too large. Maximum upload size is 200MB."}), 413


@api.errorhandler(ValueError)
def value_error(e):
    """Handle ValueError as 400 Bad Request."""
    return jsonify({"error": str(e)}), 400


@api.errorhandler(FileNotFoundError)
def file_not_found(e):
    """Handle FileNotFoundError as 404 Not Found."""
    return jsonify({"error": str(e)}), 404


@api.errorhandler(FileExistsError)
def file_exists(e):
    """Handle FileExistsError as 409 Conflict."""
    return jsonify({"error": str(e)}), 409


@api.errorhandler(Exception)
def unhandled_exception(e):
    """Handle all unhandled exceptions as 500 Internal Server Error."""
    logger.error("Unhandled exception: %s\n%s", e, traceback.format_exc())
    return jsonify({"error": str(e)}), 500


# --- Config endpoints ---


@api.route("/config", methods=["GET"])
def get_config():
    """Return the full site config as JSON."""
    config = config_ops.read_config()
    return jsonify(config)


@api.route("/config/site-name", methods=["PUT"])
def update_site_name():
    """Update the site name."""
    data = request.get_json(silent=True)
    if not data or "value" not in data:
        return jsonify({"error": "Missing JSON body with 'value' key"}), 400
    value = data["value"]
    if not value or not value.strip():
        return jsonify({"error": "Site name cannot be empty"}), 400
    config_ops.update_site_name(value)
    return jsonify({"site_name": value})


@api.route("/config/footer", methods=["PUT"])
def update_footer():
    """Update the footer copyright text."""
    data = request.get_json(silent=True)
    if not data or "value" not in data:
        return jsonify({"error": "Missing JSON body with 'value' key"}), 400
    config_ops.update_footer_copyright(data["value"])
    return jsonify({"copyright": data["value"]})


# --- Navigation endpoints ---


@api.route("/navigation", methods=["GET"])
def get_navigation():
    """Return the list of navigation items."""
    return jsonify(config_ops.get_nav_items())


@api.route("/navigation", methods=["POST"])
def add_navigation():
    """Add a new navigation item."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing 'label' and/or 'url' in request body"}), 400
    label = data.get("label")
    url = data.get("url")
    if not isinstance(label, str) or not label.strip():
        return jsonify({"error": "Label must be a non-empty string"}), 400
    if not isinstance(url, str) or not url.strip():
        return jsonify({"error": "URL must be a non-empty string"}), 400
    config_ops.add_nav_item(label, url)
    return jsonify(config_ops.get_nav_items()), 201


@api.route("/navigation/<int:index>", methods=["PUT"])
def update_navigation(index):
    """Update a navigation item at the given index."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing 'label' and/or 'url' in request body"}), 400
    label = data.get("label")
    url = data.get("url")
    if not isinstance(label, str) or not label.strip():
        return jsonify({"error": "Label must be a non-empty string"}), 400
    if not isinstance(url, str) or not url.strip():
        return jsonify({"error": "URL must be a non-empty string"}), 400
    try:
        config_ops.update_nav_item(index, data["label"], data["url"])
    except IndexError:
        return jsonify({"error": f"Navigation item at index {index} not found"}), 404
    return jsonify(config_ops.get_nav_items())


@api.route("/navigation/<int:index>", methods=["DELETE"])
def delete_navigation(index):
    """Delete a navigation item at the given index."""
    try:
        config_ops.delete_nav_item(index)
    except IndexError:
        return jsonify({"error": f"Navigation item at index {index} not found"}), 404
    return jsonify(config_ops.get_nav_items())


@api.route("/navigation/reorder", methods=["PUT"])
def reorder_navigation():
    """Reorder navigation items."""
    data = request.get_json(silent=True)
    if not data or "order" not in data:
        return jsonify({"error": "Missing 'order' in request body"}), 400
    order = data["order"]
    if not isinstance(order, list):
        return jsonify({"error": "'order' must be a list"}), 400
    current_nav = config_ops.get_nav_items()
    if len(order) != len(current_nav):
        return jsonify({"error": f"Order list length ({len(order)}) does not match number of navigation items ({len(current_nav)})"}), 400
    try:
        config_ops.reorder_nav_items(order)
    except (ValueError, IndexError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(config_ops.get_nav_items())


# --- Category endpoints ---


@api.route("/categories", methods=["GET"])
def get_categories():
    """Return the list of categories with metadata."""
    return jsonify(file_ops.list_categories())


@api.route("/categories", methods=["POST"])
def create_category():
    """Create a new category."""
    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "Missing 'name' in request body"}), 400
    try:
        category = file_ops.create_category(data["name"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(category), 201


@api.route("/categories/<name>", methods=["PUT"])
def rename_category(name):
    """Rename a category."""
    data = request.get_json(silent=True)
    if not data or not data.get("name"):
        return jsonify({"error": "Missing 'name' in request body"}), 400
    try:
        category = file_ops.rename_category(name, data["name"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(category)


@api.route("/categories/<name>", methods=["DELETE"])
def delete_category(name):
    """Delete a category."""
    data = request.get_json(silent=True)
    if not data or not data.get("confirm"):
        return jsonify({"error": "Deletion must be confirmed with {\"confirm\": true}"}), 400
    file_ops.delete_category(name, confirm=True)
    return jsonify({"deleted": name})


# --- Image endpoints ---


@api.route("/categories/<name>/images", methods=["GET"])
def get_images(name):
    """Return sorted list of images in a category."""
    images = file_ops.list_images(name)
    return jsonify(images)


@api.route("/categories/<name>/images", methods=["POST"])
def upload_images(name):
    """Upload one or more images to a category via multipart file upload.

    Validates each file's extension before saving. Invalid files are skipped
    and reported in the warnings list. Returns partial results if some files
    succeed and others fail.
    """
    from pathlib import Path as _Path

    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No image files provided"}), 400

    from PIL import Image as _Image
    import io as _io

    added = []
    warnings = []
    for f in files:
        if not f.filename:
            continue
        ext = _Path(f.filename).suffix.lower()
        if ext not in IMAGE_EXTS:
            warnings.append(f"Skipped '{f.filename}': unsupported extension '{ext}'")
            continue
        # Read file content for validation
        content = f.read()
        if len(content) == 0:
            warnings.append(f"Skipped '{f.filename}': file is empty (zero bytes)")
            continue
        # Validate file is actually an image
        try:
            _Image.open(_io.BytesIO(content)).verify()
        except Exception:
            warnings.append(f"Skipped '{f.filename}': file is not a valid image")
            continue
        # Reset stream for saving
        f.seek(0)
        image = file_ops.add_image(name, f)
        added.append(image)

    if not added and warnings:
        return jsonify({"error": "No valid image files provided", "warnings": warnings}), 400
    if not added:
        return jsonify({"error": "No valid image files provided"}), 400

    result = added
    if warnings:
        result = {"images": added, "warnings": warnings}
    return jsonify(result), 201


@api.route("/categories/<name>/images/reorder", methods=["PUT"])
def reorder_images(name):
    """Reorder images in a category."""
    data = request.get_json(silent=True)
    if not data or "order" not in data:
        return jsonify({"error": "Missing 'order' in request body"}), 400
    order = data["order"]
    if not isinstance(order, list):
        return jsonify({"error": "'order' must be a list of filenames"}), 400
    current_images = file_ops.list_images(name)
    if len(order) != len(current_images):
        return jsonify({"error": f"Order list length ({len(order)}) does not match number of images ({len(current_images)})"}), 400
    rename_map = file_ops.reorder_images(name, order)
    return jsonify(rename_map)


@api.route("/categories/<name>/images/<filename>", methods=["DELETE"])
def delete_image(name, filename):
    """Delete an image and its thumbnail from a category."""
    file_ops.delete_image(name, filename)
    return jsonify({"deleted": filename})


# --- Deploy endpoints ---


@api.route("/deploy/preflight", methods=["GET"])
def deploy_preflight():
    """Return preflight status for deploy."""
    result = git_ops.get_deploy_preflight()
    return jsonify(result)


@api.route("/deploy", methods=["POST"])
def deploy():
    """Run the full deploy pipeline."""
    data = request.get_json(silent=True)
    message = (data.get("message") if data else None) or "Update portfolio"
    result = git_ops.deploy(message)
    return jsonify(result)
