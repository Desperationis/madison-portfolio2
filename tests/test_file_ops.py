"""Tests for gui.file_ops module."""

import io

import pytest
from PIL import Image

from gui.file_ops import (
    ART_DIR,
    add_image,
    create_category,
    delete_category,
    delete_image,
    list_categories,
    list_images,
    rename_category,
    reorder_images,
    validate_category_name,
)


EXPECTED_CATEGORIES = [
    "Character works",
    "Finished Pieces",
    "Line Art",
    "Storyboard Panels",
    "The Guardian Press Works",
    "Volition Wingspan Works",
    "sketches",
]


def test_list_categories_names():
    """list_categories returns all expected category names, sorted."""
    cats = list_categories()
    names = [c["name"] for c in cats]
    assert names == EXPECTED_CATEGORIES


def test_list_categories_structure():
    """Each category dict has the required keys with correct types."""
    cats = list_categories()
    for cat in cats:
        assert isinstance(cat["name"], str)
        assert isinstance(cat["image_count"], int)
        assert isinstance(cat["has_thumbnails"], bool)
        assert cat["thumbnail_url"] is None or isinstance(cat["thumbnail_url"], str)
        assert cat["image_count"] >= 0


# --- validate_category_name tests ---


def test_validate_category_name_strips_whitespace():
    assert validate_category_name("  My Category  ") == "My Category"


def test_validate_category_name_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_category_name("")


def test_validate_category_name_whitespace_only():
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_category_name("   ")


@pytest.mark.parametrize("name", [".", ".."])
def test_validate_category_name_dots(name):
    with pytest.raises(ValueError, match="cannot be"):
        validate_category_name(name)


@pytest.mark.parametrize("name", ["a/b", "a\\b", "a\0b"])
def test_validate_category_name_bad_chars(name):
    with pytest.raises(ValueError, match="cannot contain"):
        validate_category_name(name)


def test_validate_category_name_starts_with_dot():
    with pytest.raises(ValueError, match="cannot start with"):
        validate_category_name(".hidden")


def test_validate_category_name_too_long():
    with pytest.raises(ValueError, match="cannot exceed"):
        validate_category_name("a" * 256)


def test_validate_category_name_valid():
    assert validate_category_name("New Category") == "New Category"


# --- create_category tests ---


def test_create_category(tmp_path, monkeypatch):
    """Create a category and verify directories and return dict."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    result = create_category("Test Category")
    cat_dir = tmp_path / "Test Category"
    assert cat_dir.is_dir()
    assert (cat_dir / "thumbnails").is_dir()
    assert result == {
        "name": "Test Category",
        "image_count": 0,
        "has_thumbnails": True,
        "thumbnail_url": None,
    }


def test_create_category_already_exists(tmp_path, monkeypatch):
    """Creating a category that already exists raises FileExistsError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "Existing").mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        create_category("Existing")


# --- rename_category tests ---


def test_rename_category(tmp_path, monkeypatch):
    """Rename a category and verify old dir gone, new dir exists."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    old_dir = tmp_path / "Old Name"
    old_dir.mkdir()
    (old_dir / "thumbnails").mkdir()
    # Add a dummy image
    (old_dir / "art_1.jpg").write_bytes(b"\xff\xd8")

    result = rename_category("Old Name", "New Name")

    assert not old_dir.exists()
    assert (tmp_path / "New Name").is_dir()
    assert (tmp_path / "New Name" / "thumbnails").is_dir()
    assert (tmp_path / "New Name" / "art_1.jpg").exists()
    assert result["name"] == "New Name"
    assert result["image_count"] == 1
    assert result["has_thumbnails"] is True
    assert result["thumbnail_url"] == "/art/New Name/art_1.jpg"


def test_rename_category_old_not_found(tmp_path, monkeypatch):
    """Renaming a non-existent category raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        rename_category("Nonexistent", "Whatever")


def test_rename_category_new_already_exists(tmp_path, monkeypatch):
    """Renaming to an existing name raises FileExistsError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "A").mkdir()
    (tmp_path / "B").mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        rename_category("A", "B")


# --- delete_category tests ---


def test_delete_category(tmp_path, monkeypatch):
    """Delete a category with confirm=True removes directory and contents."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "To Delete"
    cat_dir.mkdir()
    (cat_dir / "thumbnails").mkdir()
    (cat_dir / "art_1.jpg").write_bytes(b"\xff\xd8")

    delete_category("To Delete", confirm=True)

    assert not cat_dir.exists()


def test_delete_category_no_confirm(tmp_path, monkeypatch):
    """Delete without confirm raises ValueError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "X").mkdir()
    with pytest.raises(ValueError, match="must be confirmed"):
        delete_category("X")


def test_delete_category_not_found(tmp_path, monkeypatch):
    """Deleting a non-existent category raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        delete_category("Nope", confirm=True)


# --- list_images tests ---


def test_list_images_sort_order(tmp_path, monkeypatch):
    """list_images returns images sorted by numeric suffix."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "sketches"
    cat_dir.mkdir()
    # Create images with numeric suffixes (out of order on disk)
    for name in ["art_3.jpg", "art_1.jpg", "art_10.jpg", "art_2.jpg"]:
        (cat_dir / name).write_bytes(b"\xff\xd8")

    result = list_images("sketches")
    filenames = [img["filename"] for img in result]
    assert filenames == ["art_1.jpg", "art_2.jpg", "art_3.jpg", "art_10.jpg"]


def test_list_images_structure(tmp_path, monkeypatch):
    """Each image dict has the required keys with correct types."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "My Art"
    cat_dir.mkdir()
    (cat_dir / "pic_1.png").write_bytes(b"\x89PNG")

    result = list_images("My Art")
    assert len(result) == 1
    img = result[0]
    assert img["filename"] == "pic_1.png"
    assert img["sort_key"] == 1
    assert img["has_thumbnail"] is False
    assert img["thumbnail_filename"] is None
    assert img["size_bytes"] == 4


def test_list_images_url_encoding(tmp_path, monkeypatch):
    """URLs with spaces are properly encoded."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "My Art"
    cat_dir.mkdir()
    (cat_dir / "my pic.jpg").write_bytes(b"\xff\xd8")

    result = list_images("My Art")
    img = result[0]
    assert img["full_url"] == "/art/My%20Art/my%20pic.jpg"
    assert img["thumbnail_url"] == img["full_url"]  # no thumbnail → fallback


def test_list_images_with_thumbnails(tmp_path, monkeypatch):
    """Images with matching thumbnails get correct thumbnail URLs."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "cats"
    cat_dir.mkdir()
    thumb_dir = cat_dir / "thumbnails"
    thumb_dir.mkdir()
    (cat_dir / "cat_1.jpg").write_bytes(b"\xff\xd8")
    (thumb_dir / "cat_1.jpg").write_bytes(b"\xff\xd8")

    result = list_images("cats")
    img = result[0]
    assert img["has_thumbnail"] is True
    assert img["thumbnail_filename"] == "cat_1.jpg"
    assert img["thumbnail_url"] == "/art/cats/thumbnails/cat_1.jpg"


def test_list_images_nonexistent_category(tmp_path, monkeypatch):
    """list_images raises FileNotFoundError for missing category."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        list_images("nope")


def test_list_images_no_sort_key_last(tmp_path, monkeypatch):
    """Images without a numeric suffix sort after those with one."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "misc"
    cat_dir.mkdir()
    (cat_dir / "art_1.jpg").write_bytes(b"\xff\xd8")
    (cat_dir / "landscape.jpg").write_bytes(b"\xff\xd8")

    result = list_images("misc")
    filenames = [img["filename"] for img in result]
    assert filenames == ["art_1.jpg", "landscape.jpg"]


# --- add_image tests ---


class MockFileStorage:
    """Minimal mock of Flask's FileStorage for testing."""

    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self._data = data

    def save(self, path):
        from pathlib import Path
        Path(path).write_bytes(self._data)


def _make_test_jpeg() -> bytes:
    """Create a small valid JPEG in memory."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, "JPEG")
    return buf.getvalue()


def test_add_image(tmp_path, monkeypatch):
    """Add an image and verify file and thumbnail exist on disk."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "TestCat"
    cat_dir.mkdir()

    jpeg_data = _make_test_jpeg()
    storage = MockFileStorage("photo_1.jpg", jpeg_data)
    result = add_image("TestCat", storage)

    assert (cat_dir / "photo_1.jpg").exists()
    assert (cat_dir / "thumbnails" / "photo_1.jpg").exists()
    assert result["filename"] == "photo_1.jpg"
    assert result["has_thumbnail"] is True
    assert result["sort_key"] == 1
    assert result["size_bytes"] > 0


def test_add_image_duplicate_name(tmp_path, monkeypatch):
    """Uploading a file with an existing name gets a unique suffix."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Dupes"
    cat_dir.mkdir()
    (cat_dir / "art.jpg").write_bytes(b"\xff\xd8")

    jpeg_data = _make_test_jpeg()
    storage = MockFileStorage("art.jpg", jpeg_data)
    result = add_image("Dupes", storage)

    assert result["filename"] == "art_1.jpg"
    assert (cat_dir / "art_1.jpg").exists()


def test_add_image_bad_extension(tmp_path, monkeypatch):
    """Uploading a file with an unsupported extension raises ValueError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Bad"
    cat_dir.mkdir()

    storage = MockFileStorage("file.txt", b"hello")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        add_image("Bad", storage)


def test_add_image_nonexistent_category(tmp_path, monkeypatch):
    """Adding to a non-existent category raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    storage = MockFileStorage("art.jpg", _make_test_jpeg())
    with pytest.raises(FileNotFoundError, match="does not exist"):
        add_image("Nope", storage)


# --- delete_image tests ---


def test_delete_image(tmp_path, monkeypatch):
    """Delete an image and verify both image and thumbnail are removed."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "DelCat"
    cat_dir.mkdir()

    # Add an image first
    jpeg_data = _make_test_jpeg()
    storage = MockFileStorage("photo_1.jpg", jpeg_data)
    add_image("DelCat", storage)

    assert (cat_dir / "photo_1.jpg").exists()
    assert (cat_dir / "thumbnails" / "photo_1.jpg").exists()

    delete_image("DelCat", "photo_1.jpg")

    assert not (cat_dir / "photo_1.jpg").exists()
    assert not (cat_dir / "thumbnails" / "photo_1.jpg").exists()


def test_delete_image_not_found(tmp_path, monkeypatch):
    """Deleting a non-existent image raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Empty"
    cat_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        delete_image("Empty", "nope.jpg")


# --- reorder_images tests ---


def test_reorder_images(tmp_path, monkeypatch):
    """Reorder 3 images and verify new names and thumbnails match."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Reorder"
    cat_dir.mkdir()
    thumb_dir = cat_dir / "thumbnails"
    thumb_dir.mkdir()

    # Create 3 images and thumbnails
    for name in ["a_1.jpg", "b_2.jpg", "c_3.jpg"]:
        (cat_dir / name).write_bytes(b"\xff\xd8")
        (thumb_dir / name).write_bytes(b"\xff\xd8")

    # Reorder: c first, then a, then b
    result = reorder_images("Reorder", ["c_3.jpg", "a_1.jpg", "b_2.jpg"])

    assert result == {
        "c_3.jpg": "c_1.jpg",
        "a_1.jpg": "a_2.jpg",
        "b_2.jpg": "b_3.jpg",
    }

    # Verify files on disk
    assert (cat_dir / "c_1.jpg").exists()
    assert (cat_dir / "a_2.jpg").exists()
    assert (cat_dir / "b_3.jpg").exists()
    assert not (cat_dir / "c_3.jpg").exists()
    assert not (cat_dir / "a_1.jpg").exists()
    assert not (cat_dir / "b_2.jpg").exists()

    # Verify thumbnails renamed in sync
    assert (thumb_dir / "c_1.jpg").exists()
    assert (thumb_dir / "a_2.jpg").exists()
    assert (thumb_dir / "b_3.jpg").exists()
    assert not (thumb_dir / "c_3.jpg").exists()
    assert not (thumb_dir / "a_1.jpg").exists()
    assert not (thumb_dir / "b_2.jpg").exists()
