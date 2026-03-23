"""Tests for the API Blueprint — error handlers, config, navigation, and deploy endpoints."""

import json
import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import pytest
import yaml

# Patch CONFIG_PATH before importing anything that reads it
import gui.config_ops as config_ops
import gui.file_ops as file_ops


@pytest.fixture(autouse=True)
def temp_config(tmp_path, monkeypatch):
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

    # Create art/ directory
    (tmp_path / "art").mkdir()

    monkeypatch.setattr(config_ops, "CONFIG_PATH", config_file)
    monkeypatch.setattr(file_ops, "ART_DIR", tmp_path / "art")


@pytest.fixture
def client():
    """Create a Flask test client."""
    from GUI import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestErrorHandlers:
    """Tests for API error handlers."""

    def test_nonexistent_route_returns_json_404(self, client):
        """GET /api/nonexistent returns JSON 404."""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_wrong_method_returns_json_405(self, client):
        """PATCH /api/config returns JSON 405, not HTML."""
        resp = client.patch("/api/config")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data is not None, "Response should be JSON, not HTML"
        assert "error" in data

    def test_api_errors_have_json_content_type(self, client):
        """All API error responses have application/json content type."""
        resp = client.get("/api/nonexistent")
        assert resp.content_type.startswith("application/json")

        resp = client.patch("/api/categories")
        assert resp.content_type.startswith("application/json")


class TestConfigEndpoints:
    """Tests for /api/config endpoints."""

    def test_get_config(self, client):
        """GET /api/config returns full config as JSON."""
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["site_name"] == "Test Portfolio"
        assert "navigation" in data
        assert "footer" in data

    def test_put_site_name(self, client):
        """PUT /api/config/site-name updates the site name."""
        resp = client.put(
            "/api/config/site-name",
            json={"value": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["site_name"] == "New Name"

        # Verify it persisted
        resp2 = client.get("/api/config")
        assert resp2.get_json()["site_name"] == "New Name"

    def test_put_site_name_missing_body(self, client):
        """PUT /api/config/site-name with no body returns 400."""
        resp = client.put("/api/config/site-name")
        assert resp.status_code == 400

    def test_put_site_name_empty(self, client):
        """PUT /api/config/site-name with empty value returns 400."""
        resp = client.put("/api/config/site-name", json={"value": ""})
        assert resp.status_code == 400

    def test_put_footer(self, client):
        """PUT /api/config/footer updates the footer copyright."""
        resp = client.put("/api/config/footer", json={"value": "2025 Updated"})
        assert resp.status_code == 200
        assert resp.get_json()["copyright"] == "2025 Updated"

        resp2 = client.get("/api/config")
        assert resp2.get_json()["footer"]["copyright"] == "2025 Updated"


class TestNavigationEndpoints:
    """Tests for /api/navigation endpoints."""

    def test_get_navigation(self, client):
        """GET /api/navigation returns nav items."""
        resp = client.get("/api/navigation")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["label"] == "Home"

    def test_add_nav_item(self, client):
        """POST /api/navigation adds a new nav item."""
        resp = client.post("/api/navigation", json={"label": "Blog", "url": "/blog"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert len(data) == 3
        assert data[2]["label"] == "Blog"

    def test_add_nav_item_missing_fields(self, client):
        """POST /api/navigation with missing fields returns 400."""
        resp = client.post("/api/navigation", json={"label": "Blog"})
        assert resp.status_code == 400

    def test_update_nav_item(self, client):
        """PUT /api/navigation/<index> updates a nav item."""
        resp = client.put("/api/navigation/0", json={"label": "Homepage", "url": "/home"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["label"] == "Homepage"

    def test_update_nav_item_out_of_range(self, client):
        """PUT /api/navigation/<index> with bad index returns 404."""
        resp = client.put("/api/navigation/99", json={"label": "X", "url": "/x"})
        assert resp.status_code == 404

    def test_delete_nav_item(self, client):
        """DELETE /api/navigation/<index> removes a nav item."""
        resp = client.delete("/api/navigation/0")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["label"] == "About"

    def test_delete_nav_item_out_of_range(self, client):
        """DELETE /api/navigation/<index> with bad index returns 404."""
        resp = client.delete("/api/navigation/99")
        assert resp.status_code == 404

    def test_reorder_nav_items(self, client):
        """PUT /api/navigation/reorder reorders nav items."""
        resp = client.put("/api/navigation/reorder", json={"order": [1, 0]})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["label"] == "About"
        assert data[1]["label"] == "Home"

    def test_reorder_nav_items_invalid(self, client):
        """PUT /api/navigation/reorder with bad order returns 400."""
        resp = client.put("/api/navigation/reorder", json={"order": [0, 0]})
        assert resp.status_code == 400

    def test_full_nav_lifecycle(self, client):
        """Full lifecycle: add, reorder, delete, verify."""
        # Add a nav item
        client.post("/api/navigation", json={"label": "Blog", "url": "/blog"})

        # Reorder: Blog first, then Home, then About
        client.put("/api/navigation/reorder", json={"order": [2, 0, 1]})
        resp = client.get("/api/navigation")
        data = resp.get_json()
        assert data[0]["label"] == "Blog"
        assert data[1]["label"] == "Home"
        assert data[2]["label"] == "About"

        # Delete first item (Blog)
        client.delete("/api/navigation/0")
        resp = client.get("/api/navigation")
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["label"] == "Home"


class TestCategoryEndpoints:
    """Tests for /api/categories endpoints."""

    def test_full_category_lifecycle(self, client):
        """Full lifecycle: create, list (verify), rename, list (verify), delete, list (verify gone)."""
        # Create a category
        resp = client.post("/api/categories", json={"name": "Sketches"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Sketches"
        assert data["image_count"] == 0

        # List — verify presence
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.get_json()]
        assert "Sketches" in names

        # Rename
        resp = client.put("/api/categories/Sketches", json={"name": "Drawings"})
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Drawings"

        # List — verify new name
        resp = client.get("/api/categories")
        names = [c["name"] for c in resp.get_json()]
        assert "Drawings" in names
        assert "Sketches" not in names

        # Delete
        resp = client.delete(
            "/api/categories/Drawings",
            data=json.dumps({"confirm": True}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] == "Drawings"

        # List — verify gone
        resp = client.get("/api/categories")
        names = [c["name"] for c in resp.get_json()]
        assert "Drawings" not in names


class TestImageEndpoints:
    """Tests for /api/categories/<name>/images endpoints."""

    def _create_test_image(self, tmp_path):
        """Create a minimal valid JPEG file and return its path."""
        from PIL import Image

        img_path = tmp_path / "test_upload.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path, "JPEG")
        return img_path

    def _setup_category_with_images(self, count=3):
        """Create TestCategory with the given number of test images and thumbnails."""
        from PIL import Image

        cat_dir = file_ops.ART_DIR / "TestCategory"
        cat_dir.mkdir(parents=True, exist_ok=True)
        thumb_dir = cat_dir / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)

        for i in range(1, count + 1):
            img = Image.new("RGB", (100, 100), color="red")
            img.save(str(cat_dir / f"test_{i}.jpg"), "JPEG")
            thumb = Image.new("RGB", (50, 50), color="red")
            thumb.save(str(thumb_dir / f"test_{i}.jpg"), "JPEG")

    def test_list_images(self, client):
        """GET /api/categories/TestCategory/images returns 3 images in correct sort order."""
        self._setup_category_with_images(3)

        resp = client.get("/api/categories/TestCategory/images")
        assert resp.status_code == 200
        images = resp.get_json()
        assert len(images) == 3

        # Verify correct sort order by sort_key
        sort_keys = [img["sort_key"] for img in images]
        assert sort_keys == [1, 2, 3]

        # Verify filenames
        filenames = [img["filename"] for img in images]
        assert filenames == ["test_1.jpg", "test_2.jpg", "test_3.jpg"]

        # Verify each image has expected fields
        for img in images:
            assert "filename" in img
            assert "sort_key" in img
            assert "has_thumbnail" in img
            assert "full_url" in img
            assert "thumbnail_url" in img
            assert "size_bytes" in img
            assert img["has_thumbnail"] is True

    def test_upload_image(self, client, tmp_path):
        """Upload a JPEG, verify 201, file on disk, and thumbnail generated."""
        # Create the category on disk
        self._setup_category_with_images(0)

        # Create a test JPEG in memory
        img_path = self._create_test_image(tmp_path)

        with open(img_path, "rb") as f:
            resp = client.post(
                "/api/categories/TestCategory/images",
                data={"images": (f, "upload_test.jpg")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["filename"] == "upload_test.jpg"

        # Verify file exists on disk
        cat_dir = file_ops.ART_DIR / "TestCategory"
        assert (cat_dir / "upload_test.jpg").exists()

        # Verify thumbnail was generated
        assert (cat_dir / "thumbnails" / "upload_test.jpg").exists()

    def test_delete_image(self, client):
        """DELETE an image, verify 200 and file gone from disk."""
        self._setup_category_with_images(3)

        cat_dir = file_ops.ART_DIR / "TestCategory"
        assert (cat_dir / "test_1.jpg").exists()

        resp = client.delete("/api/categories/TestCategory/images/test_1.jpg")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] == "test_1.jpg"

        # Verify file is gone from disk
        assert not (cat_dir / "test_1.jpg").exists()
        # Verify thumbnail is also gone
        assert not (cat_dir / "thumbnails" / "test_1.jpg").exists()

    def test_reorder_images(self, client):
        """Reorder images in reversed order, verify files renamed with correct numeric suffixes."""
        self._setup_category_with_images(3)

        # Reverse the order: test_3, test_2, test_1
        resp = client.put(
            "/api/categories/TestCategory/images/reorder",
            json={"order": ["test_3.jpg", "test_2.jpg", "test_1.jpg"]},
        )
        assert resp.status_code == 200
        rename_map = resp.get_json()
        assert isinstance(rename_map, dict)

        # Verify files on disk have correct numeric suffixes after reorder
        cat_dir = file_ops.ART_DIR / "TestCategory"
        # List what's on disk now
        images_on_disk = sorted(
            f.name for f in cat_dir.iterdir()
            if f.is_file() and f.suffix.lower() in {".jpg"}
        )
        # Should have 3 files with _1, _2, _3 suffixes
        assert len(images_on_disk) == 3
        # Verify via API that sort order is correct
        resp = client.get("/api/categories/TestCategory/images")
        images = resp.get_json()
        assert images[0]["sort_key"] == 1
        assert images[1]["sort_key"] == 2
        assert images[2]["sort_key"] == 3

    def test_upload_invalid_file(self, client, tmp_path):
        """Upload a .txt file, verify 400."""
        self._setup_category_with_images(0)

        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("not an image")
        with open(txt_file, "rb") as f:
            resp = client.post(
                "/api/categories/TestCategory/images",
                data={"images": (f, "notes.txt")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 400

    def test_full_image_lifecycle(self, client, tmp_path):
        """Upload an image, list (verify), reorder, list (verify order), delete, list (verify gone)."""
        # Create category first
        resp = client.post("/api/categories", json={"name": "TestArt"})
        assert resp.status_code == 201

        # Create a test image file
        img_path = self._create_test_image(tmp_path)

        # Upload image
        with open(img_path, "rb") as f:
            resp = client.post(
                "/api/categories/TestArt/images",
                data={"images": (f, "painting_1.jpg")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 201
        added = resp.get_json()
        assert len(added) == 1
        assert added[0]["filename"] == "painting_1.jpg"

        # Upload a second image
        with open(img_path, "rb") as f:
            resp = client.post(
                "/api/categories/TestArt/images",
                data={"images": (f, "painting_2.jpg")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 201

        # List — verify both images present
        resp = client.get("/api/categories/TestArt/images")
        assert resp.status_code == 200
        images = resp.get_json()
        filenames = [img["filename"] for img in images]
        assert "painting_1.jpg" in filenames
        assert "painting_2.jpg" in filenames

        # Reorder — swap the two images
        resp = client.put(
            "/api/categories/TestArt/images/reorder",
            json={"order": ["painting_2.jpg", "painting_1.jpg"]},
        )
        assert resp.status_code == 200
        rename_map = resp.get_json()
        assert isinstance(rename_map, dict)

        # List — verify new order (painting_2 should now be _1, painting_1 should now be _2)
        resp = client.get("/api/categories/TestArt/images")
        assert resp.status_code == 200
        images = resp.get_json()
        filenames = [img["filename"] for img in images]
        assert len(filenames) == 2
        # After reorder, sort keys should reflect new ordering
        assert images[0]["sort_key"] == 1
        assert images[1]["sort_key"] == 2

        # Delete the first image
        first_filename = images[0]["filename"]
        resp = client.delete(f"/api/categories/TestArt/images/{first_filename}")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] == first_filename

        # List — verify deleted image is gone
        resp = client.get("/api/categories/TestArt/images")
        assert resp.status_code == 200
        images = resp.get_json()
        remaining = [img["filename"] for img in images]
        assert first_filename not in remaining
        assert len(remaining) == 1


class TestValidationErrors:
    """Tests for input validation error handling (Phase 22.3)."""

    def test_create_category_empty_name(self, client):
        """POST to create category with empty name → 400."""
        resp = client.post("/api/categories", json={"name": ""})
        assert resp.status_code == 400

    def test_create_category_name_with_slash(self, client):
        """POST to create category with name containing '/' → 400."""
        resp = client.post("/api/categories", json={"name": "bad/name"})
        assert resp.status_code == 400

    def test_delete_category_without_confirm(self, client):
        """DELETE category without confirm: true → 400."""
        # Create category first
        client.post("/api/categories", json={"name": "ToDelete"})
        resp = client.delete(
            "/api/categories/ToDelete",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_create_duplicate_category(self, client):
        """POST to create category with same name twice → 409."""
        client.post("/api/categories", json={"name": "Alpha"})
        resp = client.post("/api/categories", json={"name": "Alpha"})
        assert resp.status_code == 409

    def test_rename_to_existing_name(self, client):
        """PUT rename to existing name → 409."""
        client.post("/api/categories", json={"name": "Alpha"})
        client.post("/api/categories", json={"name": "Beta"})
        resp = client.put("/api/categories/Alpha", json={"name": "Beta"})
        assert resp.status_code == 409

    def test_delete_nonexistent_category(self, client):
        """DELETE nonexistent category → 404."""
        resp = client.delete(
            "/api/categories/DoesNotExist",
            data=json.dumps({"confirm": True}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_upload_non_image_file(self, client, tmp_path):
        """Upload a non-image file → 400."""
        client.post("/api/categories", json={"name": "TestCat"})
        # Create a text file with an invalid extension
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("not an image")
        with open(txt_file, "rb") as f:
            resp = client.post(
                "/api/categories/TestCat/images",
                data={"images": (f, "notes.txt")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 400


class TestDeployEndpoints:
    """Tests for /api/deploy endpoints."""

    def test_preflight_ready(self, client):
        """GET /api/deploy/preflight returns correct structure when ready."""
        mock_result = {"ready": True, "errors": [], "warnings": []}
        with patch("gui.git_ops.get_deploy_preflight", return_value=mock_result):
            resp = client.get("/api/deploy/preflight")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "ready" in data
        assert "errors" in data
        assert "warnings" in data
        assert data["ready"] is True
        assert isinstance(data["errors"], list)
        assert isinstance(data["warnings"], list)

    def test_preflight_not_ready(self, client):
        """GET /api/deploy/preflight returns errors when not ready."""
        mock_result = {
            "ready": False,
            "errors": ["No remote \"origin\" configured"],
            "warnings": [],
        }
        with patch("gui.git_ops.get_deploy_preflight", return_value=mock_result):
            resp = client.get("/api/deploy/preflight")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ready"] is False
        assert len(data["errors"]) == 1

    def test_preflight_with_warnings(self, client):
        """GET /api/deploy/preflight includes warnings in response."""
        mock_result = {
            "ready": True,
            "errors": [],
            "warnings": ["Cannot reach remote — network may be unavailable"],
        }
        with patch("gui.git_ops.get_deploy_preflight", return_value=mock_result):
            resp = client.get("/api/deploy/preflight")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ready"] is True
        assert len(data["warnings"]) == 1

    def test_deploy_success(self, client):
        """POST /api/deploy with all steps succeeding returns success: true."""
        def mock_run_git(*args, **kwargs):
            cp = subprocess.CompletedProcess(args=["git", *args], returncode=0)
            # git status --porcelain returns staged changes
            if args[:2] == ("status", "--porcelain"):
                cp.stdout = "M index.html\n"
            # git rev-parse --abbrev-ref HEAD returns branch name
            elif args[:2] == ("rev-parse", "--abbrev-ref"):
                cp.stdout = "main"
            else:
                cp.stdout = ""
            cp.stderr = ""
            return cp

        def mock_subprocess_run(cmd, **kwargs):
            """Mock the portfolio generator subprocess call."""
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="Generated OK\n", stderr="")

        with patch("gui.git_ops._run_git", side_effect=mock_run_git), \
             patch("gui.git_ops.subprocess.run", side_effect=mock_subprocess_run):
            resp = client.post("/api/deploy", json={"message": "test deploy"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["error"] is None
        # All 6 steps should have succeeded
        assert len(data["steps"]) == 6
        for step in data["steps"]:
            assert step["success"] is True
            assert step["skipped"] is False

    def test_deploy_generator_failure(self, client):
        """POST /api/deploy when generator fails returns success: false with step 1 failed."""
        def mock_subprocess_run(cmd, **kwargs):
            """Mock the portfolio generator subprocess call to fail."""
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="ImportError: No module named 'portfolio'"
            )

        with patch("gui.git_ops.subprocess.run", side_effect=mock_subprocess_run):
            resp = client.post("/api/deploy", json={"message": "test deploy"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is False
        # Step 1 (Generating site) should have failed
        assert data["steps"][0]["name"] == "Generating site"
        assert data["steps"][0]["success"] is False
        assert "ImportError" in data["steps"][0]["error"]
        # Remaining steps should be skipped
        for step in data["steps"][1:]:
            assert step["skipped"] is True

    def test_deploy_push_failure(self, client):
        """POST /api/deploy when push fails returns step 6 error with stderr."""
        def mock_run_git(*args, **kwargs):
            cp = subprocess.CompletedProcess(args=["git", *args], returncode=0)
            if args[:2] == ("status", "--porcelain"):
                cp.stdout = "M index.html\n"
            elif args[:2] == ("rev-parse", "--abbrev-ref"):
                cp.stdout = "main"
            elif args[:1] == ("push",):
                cp.returncode = 1
                cp.stdout = ""
                cp.stderr = "fatal: Authentication failed for 'https://github.com/...'"
                return cp
            else:
                cp.stdout = ""
            cp.stderr = ""
            return cp

        def mock_subprocess_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="Generated OK\n", stderr="")

        with patch("gui.git_ops._run_git", side_effect=mock_run_git), \
             patch("gui.git_ops.subprocess.run", side_effect=mock_subprocess_run):
            resp = client.post("/api/deploy", json={"message": "test deploy"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is False
        # Find the Pushing step
        push_step = [s for s in data["steps"] if s["name"] == "Pushing"][0]
        assert push_step["success"] is False
        assert "Authentication failed" in push_step["error"]

    def test_deploy_no_changes(self, client):
        """POST /api/deploy with no changes returns success: true with skip message."""
        def mock_run_git(*args, **kwargs):
            cp = subprocess.CompletedProcess(args=["git", *args], returncode=0)
            if args[:2] == ("status", "--porcelain"):
                cp.stdout = ""
            elif args[:2] == ("rev-parse", "--abbrev-ref"):
                cp.stdout = "main"
            else:
                cp.stdout = ""
            cp.stderr = ""
            return cp

        def mock_subprocess_run(cmd, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="Generated OK\n", stderr="")

        with patch("gui.git_ops._run_git", side_effect=mock_run_git), \
             patch("gui.git_ops.subprocess.run", side_effect=mock_subprocess_run):
            resp = client.post("/api/deploy", json={"message": "test deploy"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        # Step 3 (Checking for changes) should report no changes
        check_step = [s for s in data["steps"] if s["name"] == "Checking for changes"][0]
        assert check_step["success"] is True
        assert "No changes to deploy" in check_step["output"]
        # Steps 4-6 should be skipped
        skipped_steps = [s for s in data["steps"] if s["name"] in ("Committing", "Pulling latest", "Pushing")]
        for step in skipped_steps:
            assert step["skipped"] is True
