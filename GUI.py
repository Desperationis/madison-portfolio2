"""Flask-based local web application for managing the art portfolio."""

import logging
import os
import shutil
import socket
import sys
import threading
import webbrowser

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from werkzeug.exceptions import HTTPException

from gui import config_ops, file_ops, git_ops
from gui.api import api
from portfolio.manifest import get_category as _get_manifest_category


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="gui/templates",
        static_folder="gui/static",
    )
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB
    app.register_blueprint(api)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Return JSON for all HTTP errors on /api/ routes."""
        if request.path.startswith("/api/"):
            return jsonify({"error": e.description}), e.code
        if e.code == 404:
            return jsonify({"error": e.description}), 404
        return e

    art_dir = os.path.join(os.getcwd(), "art")
    latest_dir = os.path.join(os.getcwd(), "latest")
    portfolio_css_dir = os.path.join(os.path.dirname(__file__), "portfolio", "css")

    @app.route("/portfolio-css/<path:filename>")
    def serve_portfolio_css(filename):
        """Serve shared CSS files from portfolio/css/."""
        return send_from_directory(portfolio_css_dir, filename)

    @app.route("/")
    def index():
        """Render the index page with category grid."""
        config = config_ops.read_config()
        categories = file_ops.list_categories()
        git_status = git_ops.check_git_status()
        return render_template(
            "index.html",
            config=config,
            categories=categories,
            git_status=git_status,
        )

    @app.route("/category/<name>")
    def category(name):
        """Render the category page with image grid."""
        config = config_ops.read_config()
        try:
            images = file_ops.list_images(name)
        except FileNotFoundError:
            abort(404, description=f"Category '{name}' not found")
        git_status = git_ops.check_git_status()
        cat_entry = _get_manifest_category(name)
        preview_filename = (cat_entry or {}).get("preview")
        return render_template(
            "category.html",
            config=config,
            category_name=name,
            images=images,
            preview_filename=preview_filename,
            git_status=git_status,
        )

    @app.after_request
    def set_csp(response):
        """Add Content-Security-Policy header to all responses."""
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
            "font-src fonts.gstatic.com"
        )
        return response

    @app.route("/art/<path:filename>")
    def serve_art(filename):
        """Serve files from the art/ directory."""
        return send_from_directory(art_dir, filename)

    @app.route("/latest/<path:filename>")
    def serve_latest(filename):
        """Serve files from the latest/ directory."""
        return send_from_directory(latest_dir, filename)

    return app


if __name__ == "__main__":
    if not os.path.isfile("config.yaml"):
        print("Error: config.yaml not found. Please run from the project root directory.", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir("art"):
        print("Error: art/ directory not found. Please run from the project root directory.", file=sys.stderr)
        sys.exit(1)

    if not shutil.which("git"):
        print("Warning: git is not available on PATH. Deploy functionality will not work.")

    app = create_app()

    # Port selection: try 5555, then 5556–5565
    port = None
    for p in range(5555, 5566):
        try:
            # Test if port is available by binding briefly
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", p))
            port = p
            break
        except OSError:
            continue

    if port is None:
        print("Error: Could not find an available port (tried 5555–5565).", file=sys.stderr)
        sys.exit(1)

    # Suppress Flask's default startup output
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Startup banner
    print(f"Portfolio Manager running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.")

    # Auto-open browser after 1 second
    threading.Timer(1.0, webbrowser.open, args=[f"http://127.0.0.1:{port}"]).start()

    try:
        app.run(host="127.0.0.1", port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
