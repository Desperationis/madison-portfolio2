"""Tests for gui.thumbnail module."""

import tempfile
from pathlib import Path

from PIL import Image

from gui.thumbnail import delete_thumbnail, generate_thumbnail


def test_generate_thumbnail_dimensions():
    """3.1.8: 1000x500 image produces 800x800 thumbnail."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Create a 1000x500 test image
        img = Image.new("RGB", (1000, 500), color=(100, 150, 200))
        image_path = tmp_path / "test_image.jpg"
        img.save(image_path, "JPEG")

        thumbnail_dir = tmp_path / "thumbnails"
        result = generate_thumbnail(image_path, thumbnail_dir)

        assert result.exists(), "Thumbnail file should exist"
        assert result == thumbnail_dir / "test_image.jpg"
        thumb = Image.open(result)
        assert thumb.size == (800, 800), f"Expected 800x800, got {thumb.size}"


def test_generate_thumbnail_rgba_to_rgb():
    """3.1.9: RGBA PNG produces RGB JPEG with no alpha."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Create an RGBA PNG
        img = Image.new("RGBA", (600, 600), color=(255, 0, 0, 128))
        image_path = tmp_path / "transparent.png"
        img.save(image_path, "PNG")

        thumbnail_dir = tmp_path / "thumbnails"
        result = generate_thumbnail(image_path, thumbnail_dir)

        assert result.exists(), "Thumbnail file should exist"
        thumb = Image.open(result)
        assert thumb.mode == "RGB", f"Expected RGB mode, got {thumb.mode}"


def test_delete_thumbnail():
    """3.2.4: Deletes a thumbnail and returns correct bool."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        thumbnail_dir = tmp_path / "thumbnails"
        thumbnail_dir.mkdir()

        # Create a fake thumbnail
        thumb = thumbnail_dir / "test.jpg"
        thumb.write_bytes(b"fake image data")
        assert thumb.exists()

        # Delete it
        result = delete_thumbnail(tmp_path, "test.jpg")
        assert result is True, "Should return True when file was deleted"
        assert not thumb.exists(), "Thumbnail should be gone"

        # Delete again — should return False
        result = delete_thumbnail(tmp_path, "test.jpg")
        assert result is False, "Should return False when file didn't exist"
