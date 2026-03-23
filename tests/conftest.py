"""Shared pytest fixtures for integration tests."""

import pytest
import yaml
from pathlib import Path
from PIL import Image

import gui.config_ops as config_ops
import gui.file_ops as file_ops


def create_test_image(path, width=100, height=100, color="red"):
    """Create a JPEG image at the given path using Pillow."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), color=color)
    img.save(str(path), "JPEG")


@pytest.fixture
def temp_art_dir(tmp_path):
    """Create a temp art directory with a TestCategory containing 3 images and thumbnails."""
    art_dir = tmp_path / "art"
    cat_dir = art_dir / "TestCategory"
    thumb_dir = cat_dir / "thumbnails"
    cat_dir.mkdir(parents=True)
    thumb_dir.mkdir()

    colors = ["red", "green", "blue"]
    for i, color in enumerate(colors, start=1):
        create_test_image(cat_dir / f"test_{i}.jpg", width=100, height=100, color=color)
        create_test_image(thumb_dir / f"test_{i}.jpg", width=50, height=50, color=color)

    yield tmp_path
    # cleanup handled by tmp_path


@pytest.fixture
def temp_config(tmp_path):
    """Create a temp config.yaml with test data."""
    config_data = {
        "site_name": "Test Site",
        "navigation": [{"label": "Home", "url": "/"}],
        "footer": {"copyright": "Test"},
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data, sort_keys=False))
    yield config_file
    # cleanup handled by tmp_path


@pytest.fixture
def app(temp_art_dir, temp_config, monkeypatch):
    """Create a Flask test client with patched paths."""
    monkeypatch.setattr(config_ops, "CONFIG_PATH", temp_config)
    monkeypatch.setattr(file_ops, "ART_DIR", temp_art_dir / "art")

    from GUI import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client
