"""Tests for page routes — index and category pages."""

import json
import re
import pytest
import yaml

import gui.config_ops as config_ops
import gui.file_ops as file_ops
import portfolio.manifest as manifest_mod


@pytest.fixture(autouse=True)
def temp_env(tmp_path, monkeypatch):
    """Create a temporary config.yaml, art/ directory, and portfolio.json for each test."""
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

    # Create manifest
    manifest_file = tmp_path / "portfolio.json"
    manifest_file.write_text(json.dumps({"categories": [
        {"name": "sketches", "preview": None, "images": ["art_1.jpg"]}
    ]}, indent=2))

    monkeypatch.setattr(config_ops, "CONFIG_PATH", config_file)
    monkeypatch.setattr(file_ops, "ART_DIR", art_dir)
    monkeypatch.setattr(manifest_mod, "MANIFEST_PATH", manifest_file)


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

    def test_card_overlay_inside_thumb(self, client):
        """Verify .card-overlay is a descendant of .thumb, not .card directly."""
        resp = client.get("/")
        html = resp.data.decode()

        # For each card, the overlay should appear inside a .thumb element
        # Find all .thumb figures — overlay must be nested inside them
        thumb_pattern = re.compile(
            r'<figure\s+class="thumb">(.*?)</figure>', re.DOTALL
        )
        thumbs = thumb_pattern.findall(html)
        assert len(thumbs) > 0, "Expected at least one .thumb figure"
        for thumb_html in thumbs:
            assert "card-overlay" in thumb_html, (
                ".card-overlay should be inside .thumb"
            )

    def test_card_link_wraps_content(self, client):
        """Verify card <a> link href points to /category/<name>."""
        resp = client.get("/")
        html = resp.data.decode()

        # Each category card should have an <a> linking to /category/<name>
        link_pattern = re.compile(
            r'<a\s+href="/category/([^"]+)">'
        )
        links = link_pattern.findall(html)
        assert len(links) > 0, "Expected at least one category link"
        assert "sketches" in links

    def test_nav_group_structure(self, client):
        """Each .nav-group contains exactly one .nav-item, one .nav-edit-btn, and one .nav-delete-btn."""
        resp = client.get("/")
        html = resp.data.decode()

        group_pattern = re.compile(
            r'<span\s+class="nav-group">(.*?)</span>', re.DOTALL
        )
        groups = group_pattern.findall(html)
        assert len(groups) > 0, "Expected at least one .nav-group"
        for group_html in groups:
            assert group_html.count('class="nav-item"') == 1, (
                "Each .nav-group should contain exactly one .nav-item"
            )
            assert group_html.count('class="nav-edit-btn"') == 1, (
                "Each .nav-group should contain exactly one .nav-edit-btn"
            )
            assert group_html.count('class="nav-delete-btn"') == 1, (
                "Each .nav-group should contain exactly one .nav-delete-btn"
            )

    def test_sortable_filter_excludes_nav_buttons(self):
        """Verify SortableJS filter includes .nav-edit-btn and .nav-delete-btn."""
        import pathlib

        js_path = pathlib.Path(__file__).resolve().parent.parent / "gui" / "static" / "editor.js"
        js = js_path.read_text()

        # Find the Sortable filter option
        filter_match = re.search(r'filter\s*:\s*"([^"]+)"', js)
        assert filter_match, "Expected a filter option in the Sortable config"
        filter_value = filter_match.group(1)
        assert ".nav-edit-btn" in filter_value, (
            "Sortable filter should include .nav-edit-btn"
        )
        assert ".nav-delete-btn" in filter_value, (
            "Sortable filter should include .nav-delete-btn"
        )

    def test_sortable_draggable_is_nav_group(self):
        """Verify SortableJS draggable option targets .nav-group."""
        import pathlib

        js_path = pathlib.Path(__file__).resolve().parent.parent / "gui" / "static" / "editor.js"
        js = js_path.read_text()

        draggable_match = re.search(r'draggable\s*:\s*"([^"]+)"', js)
        assert draggable_match, "Expected a draggable option in the Sortable config"
        assert draggable_match.group(1) == ".nav-group", (
            "Sortable draggable should be .nav-group"
        )

    def test_category_page_content_after_navigation(self, client):
        """Integration test: navigate from index to category and verify page content."""
        # Step 1: Load index and find the category link
        index_resp = client.get("/")
        assert index_resp.status_code == 200
        index_html = index_resp.data.decode()
        assert '/category/sketches' in index_html

        # Step 2: Follow the link to the category page
        resp = client.get("/category/sketches")
        assert resp.status_code == 200
        html = resp.data.decode()

        # Category name heading
        assert "sketches" in html

        # Image grid with the test image
        assert 'id="imageGrid"' in html
        assert 'data-filename="art_1.jpg"' in html
        assert 'data-full="' in html

        # Thumbnail image rendered
        assert 'src="/art/sketches/thumbnails/art_1.jpg"' in html

        # Upload zone (add images card + hidden file input)
        assert 'id="addImagesCard"' in html
        assert 'id="fileInput"' in html

        # Lightbox present
        assert 'id="lightbox"' in html

        # Drop zone overlay for drag-and-drop upload
        assert 'id="dropZone"' in html

    def test_nav_buttons_not_position_absolute(self):
        """Verify .nav-edit-btn and .nav-delete-btn do not use position: absolute in editor.css."""
        import pathlib

        css_path = pathlib.Path(__file__).resolve().parent.parent / "gui" / "static" / "editor.css"
        css = css_path.read_text()

        # Parse each rule block for .nav-edit-btn and .nav-delete-btn
        # and ensure none contain position: absolute
        block_pattern = re.compile(
            r'\.nav-(edit|delete)-btn\s*\{([^}]*)\}', re.DOTALL
        )
        blocks = block_pattern.findall(css)
        assert len(blocks) > 0, "Expected .nav-edit-btn / .nav-delete-btn rules in editor.css"
        for name, body in blocks:
            assert "position: absolute" not in body and "position:absolute" not in body, (
                f".nav-{name}-btn must not use position: absolute"
            )
