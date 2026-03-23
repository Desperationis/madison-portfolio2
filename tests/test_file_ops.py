"""Tests for gui.file_ops module."""

import io
import json

import pytest
from PIL import Image

import portfolio.manifest as manifest_mod
from gui.file_ops import (
    ART_DIR,
    add_image,
    create_category,
    crop_thumbnail,
    delete_category,
    delete_image,
    list_categories,
    list_images,
    rename_category,
    reorder_categories,
    reorder_images,
    reset_thumbnail,
    validate_category_name,
)


@pytest.fixture
def temp_manifest(tmp_path, monkeypatch):
    """Create a temporary portfolio.json and patch MANIFEST_PATH."""
    manifest_file = tmp_path / "portfolio.json"
    manifest_file.write_text(json.dumps({"categories": []}, indent=2))
    monkeypatch.setattr(manifest_mod, "MANIFEST_PATH", manifest_file)
    return manifest_file


EXPECTED_CATEGORIES = [
    "The Guardian Press Works",
    "Finished Pieces",
    "Line Art",
    "Character works",
    "Storyboard Panels",
    "Volition Wingspan Works",
    "sketches",
]


def test_list_categories_names():
    """list_categories returns all expected category names in manifest order."""
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


def test_create_category(tmp_path, monkeypatch, temp_manifest):
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


def test_create_category_already_exists(tmp_path, monkeypatch, temp_manifest):
    """Creating a category that already exists raises FileExistsError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "Existing").mkdir()
    with pytest.raises(FileExistsError, match="already exists"):
        create_category("Existing")


# --- rename_category tests ---


def test_rename_category(tmp_path, monkeypatch, temp_manifest):
    """Rename a category and verify old dir gone, new dir exists."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    old_dir = tmp_path / "Old Name"
    old_dir.mkdir()
    (old_dir / "thumbnails").mkdir()
    # Add a dummy image
    (old_dir / "art_1.jpg").write_bytes(b"\xff\xd8")

    # Set up manifest with the category
    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "Old Name", "preview": None, "images": ["art_1.jpg"]}
    ]}))

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


def test_delete_category(tmp_path, monkeypatch, temp_manifest):
    """Delete a category with confirm=True removes directory and contents."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "To Delete"
    cat_dir.mkdir()
    (cat_dir / "thumbnails").mkdir()
    (cat_dir / "art_1.jpg").write_bytes(b"\xff\xd8")

    # Set up manifest with the category
    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "To Delete", "preview": None, "images": ["art_1.jpg"]}
    ]}))

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


def test_list_images_manifest_order(tmp_path, monkeypatch, temp_manifest):
    """list_images returns images in manifest order, not filesystem order."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "sketches"
    cat_dir.mkdir()
    for name in ["art_3.jpg", "art_1.jpg", "art_10.jpg", "art_2.jpg"]:
        (cat_dir / name).write_bytes(b"\xff\xd8")

    # Manifest defines a specific order
    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "sketches", "preview": None, "images": ["art_3.jpg", "art_1.jpg", "art_10.jpg", "art_2.jpg"]}
    ]}))

    result = list_images("sketches")
    filenames = [img["filename"] for img in result]
    assert filenames == ["art_3.jpg", "art_1.jpg", "art_10.jpg", "art_2.jpg"]


def test_list_images_structure(tmp_path, monkeypatch, temp_manifest):
    """Each image dict has the required keys with correct types."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "My Art"
    cat_dir.mkdir()
    (cat_dir / "pic_1.png").write_bytes(b"\x89PNG")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "My Art", "preview": None, "images": ["pic_1.png"]}
    ]}))

    result = list_images("My Art")
    assert len(result) == 1
    img = result[0]
    assert img["filename"] == "pic_1.png"
    assert img["has_thumbnail"] is False
    assert img["thumbnail_filename"] is None
    assert img["size_bytes"] == 4


def test_list_images_url_encoding(tmp_path, monkeypatch, temp_manifest):
    """URLs with spaces are properly encoded."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "My Art"
    cat_dir.mkdir()
    (cat_dir / "my pic.jpg").write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "My Art", "preview": None, "images": ["my pic.jpg"]}
    ]}))

    result = list_images("My Art")
    img = result[0]
    assert img["full_url"] == "/art/My%20Art/my%20pic.jpg"
    assert img["thumbnail_url"] == img["full_url"]  # no thumbnail → fallback


def test_list_images_with_thumbnails(tmp_path, monkeypatch, temp_manifest):
    """Images with matching thumbnails get correct thumbnail URLs."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "cats"
    cat_dir.mkdir()
    thumb_dir = cat_dir / "thumbnails"
    thumb_dir.mkdir()
    (cat_dir / "cat_1.jpg").write_bytes(b"\xff\xd8")
    (thumb_dir / "cat_1.jpg").write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "cats", "preview": None, "images": ["cat_1.jpg"]}
    ]}))

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


def test_list_images_skips_missing_files(tmp_path, monkeypatch, temp_manifest):
    """Images in manifest but missing from disk are silently skipped."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "misc"
    cat_dir.mkdir()
    (cat_dir / "exists.jpg").write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "misc", "preview": None, "images": ["exists.jpg", "gone.jpg"]}
    ]}))

    result = list_images("misc")
    filenames = [img["filename"] for img in result]
    assert filenames == ["exists.jpg"]


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


def test_add_image(tmp_path, monkeypatch, temp_manifest):
    """Add an image and verify file, thumbnail, and manifest are updated."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "TestCat"
    cat_dir.mkdir()

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "TestCat", "preview": None, "images": []}
    ]}))

    jpeg_data = _make_test_jpeg()
    storage = MockFileStorage("photo_1.jpg", jpeg_data)
    result = add_image("TestCat", storage)

    assert (cat_dir / "photo_1.jpg").exists()
    assert (cat_dir / "thumbnails" / "photo_1.jpg").exists()
    assert result["filename"] == "photo_1.jpg"
    assert result["has_thumbnail"] is True
    assert result["size_bytes"] > 0

    # Verify manifest was updated
    manifest = json.loads(temp_manifest.read_text())
    assert "photo_1.jpg" in manifest["categories"][0]["images"]


def test_add_image_duplicate_name(tmp_path, monkeypatch, temp_manifest):
    """Uploading a file with an existing name gets a unique suffix."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Dupes"
    cat_dir.mkdir()
    (cat_dir / "art.jpg").write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "Dupes", "preview": None, "images": ["art.jpg"]}
    ]}))

    jpeg_data = _make_test_jpeg()
    storage = MockFileStorage("art.jpg", jpeg_data)
    result = add_image("Dupes", storage)

    assert result["filename"] == "art_1.jpg"
    assert (cat_dir / "art_1.jpg").exists()


def test_add_image_manifest_order(tmp_path, monkeypatch, temp_manifest):
    """Adding multiple images appends them to the manifest in upload order."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "OrderCat"
    cat_dir.mkdir()

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "OrderCat", "preview": None, "images": []}
    ]}))

    for name in ["first.jpg", "second.jpg", "third.jpg"]:
        storage = MockFileStorage(name, _make_test_jpeg())
        add_image("OrderCat", storage)

    manifest = json.loads(temp_manifest.read_text())
    assert manifest["categories"][0]["images"] == ["first.jpg", "second.jpg", "third.jpg"]


def test_delete_image_preserves_others_in_manifest(tmp_path, monkeypatch, temp_manifest):
    """Deleting one image leaves other images intact in the manifest."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Multi"
    cat_dir.mkdir()
    (cat_dir / "thumbnails").mkdir()

    # Create three images on disk
    for name in ["a.jpg", "b.jpg", "c.jpg"]:
        (cat_dir / name).write_bytes(b"\xff\xd8")
        (cat_dir / "thumbnails" / name).write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "Multi", "preview": None, "images": ["a.jpg", "b.jpg", "c.jpg"]}
    ]}))

    delete_image("Multi", "b.jpg")

    manifest = json.loads(temp_manifest.read_text())
    assert manifest["categories"][0]["images"] == ["a.jpg", "c.jpg"]


def test_delete_image_clears_preview_if_deleted(tmp_path, monkeypatch, temp_manifest):
    """Deleting the image set as preview doesn't break the manifest (preview stays as-is)."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "PrevCat"
    cat_dir.mkdir()
    (cat_dir / "thumbnails").mkdir()
    (cat_dir / "hero.jpg").write_bytes(b"\xff\xd8")
    (cat_dir / "other.jpg").write_bytes(b"\xff\xd8")
    (cat_dir / "thumbnails" / "hero.jpg").write_bytes(b"\xff\xd8")
    (cat_dir / "thumbnails" / "other.jpg").write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "PrevCat", "preview": "hero.jpg", "images": ["hero.jpg", "other.jpg"]}
    ]}))

    delete_image("PrevCat", "hero.jpg")

    manifest = json.loads(temp_manifest.read_text())
    cat = manifest["categories"][0]
    assert "hero.jpg" not in cat["images"]
    assert cat["images"] == ["other.jpg"]


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


def test_delete_image(tmp_path, monkeypatch, temp_manifest):
    """Delete an image and verify file, thumbnail, and manifest are updated."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "DelCat"
    cat_dir.mkdir()

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "DelCat", "preview": None, "images": []}
    ]}))

    # Add an image first
    jpeg_data = _make_test_jpeg()
    storage = MockFileStorage("photo_1.jpg", jpeg_data)
    add_image("DelCat", storage)

    assert (cat_dir / "photo_1.jpg").exists()
    assert (cat_dir / "thumbnails" / "photo_1.jpg").exists()

    delete_image("DelCat", "photo_1.jpg")

    assert not (cat_dir / "photo_1.jpg").exists()
    assert not (cat_dir / "thumbnails" / "photo_1.jpg").exists()

    # Verify manifest was updated
    manifest = json.loads(temp_manifest.read_text())
    assert "photo_1.jpg" not in manifest["categories"][0]["images"]


def test_delete_image_not_found(tmp_path, monkeypatch):
    """Deleting a non-existent image raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Empty"
    cat_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        delete_image("Empty", "nope.jpg")


# --- reorder_images tests ---


def test_reorder_images(tmp_path, monkeypatch, temp_manifest):
    """Reorder 3 images via manifest without renaming files on disk."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Reorder"
    cat_dir.mkdir()
    thumb_dir = cat_dir / "thumbnails"
    thumb_dir.mkdir()

    filenames = ["a.jpg", "b.jpg", "c.jpg"]

    # Create images and thumbnails on disk
    for name in filenames:
        (cat_dir / name).write_bytes(b"\xff\xd8")
        (thumb_dir / name).write_bytes(b"\xff\xd8")

    # Set up manifest with original order
    manifest_data = {"categories": [{"name": "Reorder", "preview": None, "images": filenames}]}
    temp_manifest.write_text(json.dumps(manifest_data, indent=2))

    # Reorder: c first, then a, then b
    result = reorder_images("Reorder", ["c.jpg", "a.jpg", "b.jpg"])

    # Returns identity mapping (no renames)
    assert result == {"c.jpg": "c.jpg", "a.jpg": "a.jpg", "b.jpg": "b.jpg"}

    # Verify files on disk are UNCHANGED (no renames)
    for name in filenames:
        assert (cat_dir / name).exists()
        assert (thumb_dir / name).exists()

    # Verify manifest has new order
    import portfolio.manifest as manifest_mod
    manifest = manifest_mod.read_manifest()
    cat = next(c for c in manifest["categories"] if c["name"] == "Reorder")
    assert cat["images"] == ["c.jpg", "a.jpg", "b.jpg"]


def test_reorder_images_missing_filename(tmp_path, monkeypatch, temp_manifest):
    """Reorder with a missing filename raises ValueError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "R"
    cat_dir.mkdir()
    for name in ["a.jpg", "b.jpg"]:
        (cat_dir / name).write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "R", "preview": None, "images": ["a.jpg", "b.jpg"]}
    ]}))

    with pytest.raises(ValueError, match="missing"):
        reorder_images("R", ["a.jpg"])  # b.jpg missing


def test_reorder_images_extra_filename(tmp_path, monkeypatch, temp_manifest):
    """Reorder with an extra filename raises ValueError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "R"
    cat_dir.mkdir()
    (cat_dir / "a.jpg").write_bytes(b"\xff\xd8")

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "R", "preview": None, "images": ["a.jpg"]}
    ]}))

    with pytest.raises(ValueError, match="extra"):
        reorder_images("R", ["a.jpg", "z.jpg"])


def test_reorder_images_nonexistent_category(tmp_path, monkeypatch):
    """Reorder on a non-existent category raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        reorder_images("NoSuch", ["a.jpg"])


def test_reorder_images_not_in_manifest(tmp_path, monkeypatch, temp_manifest):
    """Reorder on a category dir that exists but isn't in manifest raises FileNotFoundError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "Ghost").mkdir()

    temp_manifest.write_text(json.dumps({"categories": []}))

    with pytest.raises(FileNotFoundError, match="not found in manifest"):
        reorder_images("Ghost", ["a.jpg"])


# --- reorder_categories tests ---


def test_reorder_categories(tmp_path, monkeypatch, temp_manifest):
    """Reorder 3 categories via manifest array reorder."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)

    # Create category dirs on disk
    for name in ["Alpha", "Beta", "Gamma"]:
        (tmp_path / name).mkdir()

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "Alpha", "preview": None, "images": ["a.jpg"]},
        {"name": "Beta", "preview": None, "images": ["b.jpg"]},
        {"name": "Gamma", "preview": None, "images": ["g.jpg"]},
    ]}))

    result = reorder_categories(["Gamma", "Alpha", "Beta"])

    assert result == ["Gamma", "Alpha", "Beta"]

    # Verify manifest has new order
    manifest = json.loads(temp_manifest.read_text())
    names = [c["name"] for c in manifest["categories"]]
    assert names == ["Gamma", "Alpha", "Beta"]

    # Verify category data is preserved
    assert manifest["categories"][0]["images"] == ["g.jpg"]
    assert manifest["categories"][1]["images"] == ["a.jpg"]
    assert manifest["categories"][2]["images"] == ["b.jpg"]


def test_reorder_categories_missing_name(tmp_path, monkeypatch, temp_manifest):
    """Reorder with a missing category name raises ValueError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "A", "preview": None, "images": []},
        {"name": "B", "preview": None, "images": []},
    ]}))

    with pytest.raises(ValueError, match="missing"):
        reorder_categories(["A"])  # B missing


def test_reorder_categories_extra_name(tmp_path, monkeypatch, temp_manifest):
    """Reorder with an extra category name raises ValueError."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "A", "preview": None, "images": []},
    ]}))

    with pytest.raises(ValueError, match="extra"):
        reorder_categories(["A", "Z"])


def test_reorder_categories_same_order(tmp_path, monkeypatch, temp_manifest):
    """Reorder with the same order is a valid no-op."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)

    temp_manifest.write_text(json.dumps({"categories": [
        {"name": "X", "preview": None, "images": []},
        {"name": "Y", "preview": None, "images": []},
    ]}))

    result = reorder_categories(["X", "Y"])
    assert result == ["X", "Y"]

    manifest = json.loads(temp_manifest.read_text())
    names = [c["name"] for c in manifest["categories"]]
    assert names == ["X", "Y"]


# --- crop_thumbnail tests ---


def _make_test_image(path, width=100, height=80):
    """Create a small valid JPEG on disk."""
    img = Image.new("RGB", (width, height), color="blue")
    img.save(path, "JPEG")


def test_crop_thumbnail(tmp_path, monkeypatch):
    """Crop a region of the original image and save as thumbnail."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Art"
    cat_dir.mkdir()

    _make_test_image(cat_dir / "painting.jpg", 200, 200)

    result = crop_thumbnail("Art", "painting.jpg", x=10, y=10, size=50)

    assert (cat_dir / "thumbnails" / "painting.jpg").exists()
    assert result["filename"] == "painting.jpg"
    assert result["thumbnail_url"] == "/art/Art/thumbnails/painting.jpg"

    # Verify the thumbnail is 800x800
    thumb = Image.open(cat_dir / "thumbnails" / "painting.jpg")
    assert thumb.size == (800, 800)


def test_crop_thumbnail_no_suffix_filename(tmp_path, monkeypatch):
    """crop_thumbnail works with filenames that have no _N suffix."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Pieces"
    cat_dir.mkdir()

    _make_test_image(cat_dir / "My Cool Art.jpg", 300, 300)

    result = crop_thumbnail("Pieces", "My Cool Art.jpg", x=0, y=0, size=100)

    assert (cat_dir / "thumbnails" / "My Cool Art.jpg").exists()
    assert result["filename"] == "My Cool Art.jpg"
    assert result["thumbnail_url"] == "/art/Pieces/thumbnails/My%20Cool%20Art.jpg"


def test_crop_thumbnail_nonexistent_category(tmp_path, monkeypatch):
    """crop_thumbnail raises FileNotFoundError for missing category."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        crop_thumbnail("Nope", "img.jpg", 0, 0, 10)


def test_crop_thumbnail_nonexistent_image(tmp_path, monkeypatch):
    """crop_thumbnail raises FileNotFoundError for missing image."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "Cat").mkdir()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        crop_thumbnail("Cat", "missing.jpg", 0, 0, 10)


# --- reset_thumbnail tests ---


def test_reset_thumbnail(tmp_path, monkeypatch):
    """Reset thumbnail regenerates it from the original image."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Art"
    cat_dir.mkdir()

    _make_test_image(cat_dir / "drawing.jpg", 150, 150)

    result = reset_thumbnail("Art", "drawing.jpg")

    assert (cat_dir / "thumbnails" / "drawing.jpg").exists()
    assert result["filename"] == "drawing.jpg"
    assert result["thumbnail_url"] == "/art/Art/thumbnails/drawing.jpg"


def test_reset_thumbnail_no_suffix_filename(tmp_path, monkeypatch):
    """reset_thumbnail works with filenames that have no _N suffix."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    cat_dir = tmp_path / "Sketches"
    cat_dir.mkdir()

    _make_test_image(cat_dir / "Character Design Final.jpg", 200, 200)

    result = reset_thumbnail("Sketches", "Character Design Final.jpg")

    assert (cat_dir / "thumbnails" / "Character Design Final.jpg").exists()
    assert result["filename"] == "Character Design Final.jpg"
    assert result["thumbnail_url"] == "/art/Sketches/thumbnails/Character%20Design%20Final.jpg"


def test_reset_thumbnail_nonexistent_category(tmp_path, monkeypatch):
    """reset_thumbnail raises FileNotFoundError for missing category."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        reset_thumbnail("Nope", "img.jpg")


def test_reset_thumbnail_nonexistent_image(tmp_path, monkeypatch):
    """reset_thumbnail raises FileNotFoundError for missing image."""
    monkeypatch.setattr("gui.file_ops.ART_DIR", tmp_path)
    (tmp_path / "Cat").mkdir()
    with pytest.raises(FileNotFoundError, match="does not exist"):
        reset_thumbnail("Cat", "missing.jpg")
