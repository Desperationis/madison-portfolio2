"""Tests for page routes — index and category pages."""

import pytest
import yaml

import gui.config_ops as config_ops
import gui.file_ops as file_ops


@pytest.fixture(autouse=True)
def temp_env(tmp_path, monkeypatch):
    """Create a temporary config.yaml and art/ directory for each test."""
    config_data = {
        "site_name": "Test Portfolio",
        "navigation": [
            {"label": "Home", "url": "/"},
            {"label": "About", "url": "/about"},
        ],
        "footer": {"copyright": "2024 Test"},
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data, sort_keys=False))

    art_dir = tmp_path / "art"
    art_dir.mkdir()

    # Create a "sketches" category with one image
    sketches = art_dir / "sketches"
    sketches.mkdir()
    (sketches / "thumbnails").mkdir()
    (sketches / "art_1.jpg").write_bytes(b"\xff\xd8fake-jpg")
    (sketches / "thumbnails" / "art_1.jpg").write_bytes(b"\xff\xd8fake-thumb")

    monkeypatch.setattr(config_ops, "CONFIG_PATH", config_file)
    monkeypatch.setattr(file_ops, "ART_DIR", art_dir)


@pytest.fixture
def client():
    """Create a Flask test client."""
    from GUI import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestRoutes:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_category_returns_200(self, client):
        resp = client.get("/category/sketches")
        assert resp.status_code == 200

    def test_category_nonexistent_returns_404(self, client):
        resp = client.get("/category/nonexistent")
        assert resp.status_code == 404

    def test_category_lightbox_elements(self, client):
        """Verify lightbox HTML and JS are present in the category page."""
        resp = client.get("/category/sketches")
        html = resp.data.decode()

        # Lightbox HTML elements
        assert 'id="lightbox"' in html
        assert 'id="lightboxImg"' in html
        assert 'id="prevBtn"' in html
        assert 'id="nextBtn"' in html
        assert 'id="closeBtn"' in html
        assert 'class="lightbox"' in html

        # Lightbox CSS
        assert ".lightbox{" in html or ".lightbox {" in html
        assert ".lightbox.open{display:flex}" in html or ".lightbox.open" in html

        # Lightbox JS functions
        assert "function openAt(" in html
        assert "function closeLightbox(" in html
        assert "function nextImg(" in html
        assert "function prevImg(" in html

        # Keyboard navigation
        assert "ArrowRight" in html
        assert "ArrowLeft" in html
        assert "Escape" in html

        # Image tile with data-full attribute for lightbox
        assert 'data-full="' in html
        assert 'class="tile"' in html
