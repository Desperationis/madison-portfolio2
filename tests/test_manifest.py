"""Tests for portfolio.manifest module — read, write, validate, and helpers."""

import json

import pytest

import portfolio.manifest as manifest_mod
from portfolio.manifest import (
    ManifestError,
    get_category,
    migrate_to_manifest,
    read_manifest,
    validate_manifest,
    write_manifest,
)


@pytest.fixture
def manifest_file(tmp_path, monkeypatch):
    """Create a temporary portfolio.json and patch MANIFEST_PATH."""
    f = tmp_path / "portfolio.json"
    monkeypatch.setattr(manifest_mod, "MANIFEST_PATH", f)
    return f


VALID_MANIFEST = {
    "categories": [
        {"name": "Sketches", "preview": None, "images": ["a.jpg", "b.jpg"]},
        {"name": "Paintings", "preview": "sunset.jpg", "images": ["sunset.jpg", "ocean.jpg"]},
    ]
}


# --- Round-trip read/write ---


class TestRoundTrip:
    def test_write_then_read(self, manifest_file):
        """Write a manifest and read it back — data should be identical."""
        write_manifest(VALID_MANIFEST)
        result = read_manifest()
        assert result == VALID_MANIFEST

    def test_write_preserves_unicode(self, manifest_file):
        """Unicode characters in names survive a round-trip."""
        data = {"categories": [{"name": "日本語アート", "preview": None, "images": ["画像.jpg"]}]}
        write_manifest(data)
        result = read_manifest()
        assert result["categories"][0]["name"] == "日本語アート"
        assert result["categories"][0]["images"] == ["画像.jpg"]

    def test_write_empty_categories(self, manifest_file):
        """An empty categories list round-trips correctly."""
        data = {"categories": []}
        write_manifest(data)
        assert read_manifest() == data

    def test_write_creates_file(self, manifest_file):
        """write_manifest creates the file if it doesn't exist."""
        assert not manifest_file.exists()
        write_manifest({"categories": []})
        assert manifest_file.exists()

    def test_write_overwrites_existing(self, manifest_file):
        """write_manifest overwrites existing content."""
        write_manifest({"categories": [{"name": "A", "preview": None, "images": []}]})
        write_manifest({"categories": [{"name": "B", "preview": None, "images": []}]})
        result = read_manifest()
        assert len(result["categories"]) == 1
        assert result["categories"][0]["name"] == "B"


# --- Atomic write ---


class TestAtomicWrite:
    def test_no_temp_file_left_after_write(self, manifest_file):
        """The .tmp file should not exist after a successful write."""
        write_manifest({"categories": []})
        tmp_file = manifest_file.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_invalid_data_does_not_overwrite(self, manifest_file):
        """Writing invalid data should not corrupt an existing manifest."""
        write_manifest(VALID_MANIFEST)
        with pytest.raises(ManifestError):
            write_manifest({"categories": "not a list"})
        # Original data should still be intact
        result = read_manifest()
        assert result == VALID_MANIFEST


# --- Validation ---


class TestValidation:
    def test_valid_manifest(self):
        """A well-formed manifest passes validation."""
        validate_manifest(VALID_MANIFEST)  # Should not raise

    def test_not_a_dict(self):
        with pytest.raises(ManifestError, match="must be a JSON object"):
            validate_manifest([])

    def test_missing_categories_key(self):
        with pytest.raises(ManifestError, match="'categories' key"):
            validate_manifest({})

    def test_categories_not_a_list(self):
        with pytest.raises(ManifestError, match="must be a list"):
            validate_manifest({"categories": "oops"})

    def test_category_not_a_dict(self):
        with pytest.raises(ManifestError, match="must be an object"):
            validate_manifest({"categories": ["not a dict"]})

    def test_category_missing_name(self):
        with pytest.raises(ManifestError, match="'name' string"):
            validate_manifest({"categories": [{"images": [], "preview": None}]})

    def test_category_name_not_string(self):
        with pytest.raises(ManifestError, match="'name' string"):
            validate_manifest({"categories": [{"name": 123, "images": [], "preview": None}]})

    def test_category_missing_images(self):
        with pytest.raises(ManifestError, match="'images' list"):
            validate_manifest({"categories": [{"name": "A", "preview": None}]})

    def test_category_images_not_list(self):
        with pytest.raises(ManifestError, match="'images' list"):
            validate_manifest({"categories": [{"name": "A", "images": "nope", "preview": None}]})

    def test_category_images_contain_non_string(self):
        with pytest.raises(ManifestError, match="all images must be strings"):
            validate_manifest({"categories": [{"name": "A", "images": [123], "preview": None}]})

    def test_category_missing_preview(self):
        with pytest.raises(ManifestError, match="'preview' field"):
            validate_manifest({"categories": [{"name": "A", "images": []}]})

    def test_category_preview_wrong_type(self):
        with pytest.raises(ManifestError, match="'preview' must be a string or null"):
            validate_manifest({"categories": [{"name": "A", "images": [], "preview": 42}]})

    def test_category_preview_null_is_valid(self):
        validate_manifest({"categories": [{"name": "A", "images": [], "preview": None}]})

    def test_category_preview_string_is_valid(self):
        validate_manifest({"categories": [{"name": "A", "images": ["x.jpg"], "preview": "x.jpg"}]})


# --- read_manifest edge cases ---


class TestReadManifest:
    def test_file_not_found(self, manifest_file):
        """read_manifest raises FileNotFoundError when file is missing."""
        with pytest.raises(FileNotFoundError):
            read_manifest()

    def test_invalid_json(self, manifest_file):
        """read_manifest raises on malformed JSON."""
        manifest_file.write_text("{broken json")
        with pytest.raises(json.JSONDecodeError):
            read_manifest()

    def test_valid_json_but_invalid_manifest(self, manifest_file):
        """read_manifest raises ManifestError on structurally invalid data."""
        manifest_file.write_text(json.dumps({"not_categories": []}))
        with pytest.raises(ManifestError):
            read_manifest()


# --- Helper functions ---


class TestGetCategory:
    def test_found(self, manifest_file):
        write_manifest(VALID_MANIFEST)
        cat = get_category("Sketches")
        assert cat is not None
        assert cat["name"] == "Sketches"
        assert cat["images"] == ["a.jpg", "b.jpg"]

    def test_not_found(self, manifest_file):
        write_manifest(VALID_MANIFEST)
        assert get_category("Nonexistent") is None


# --- Migration ---


class TestMigration:
    """Test migrate_to_manifest() — filesystem scan to manifest conversion."""

    def _make_image(self, path):
        """Create a tiny placeholder file at the given path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xd8\xff\xe0")  # minimal JPEG header

    def test_basic_migration(self, manifest_file, tmp_path):
        """Migration with _N suffixed files produces correctly ordered manifest."""
        art = tmp_path / "art"

        # Category: Sketches — files with _N suffixes
        self._make_image(art / "Sketches" / "cat_2.jpg")
        self._make_image(art / "Sketches" / "dog_1.jpg")
        self._make_image(art / "Sketches" / "bird_3.jpg")
        (art / "Sketches" / "thumbnails").mkdir()

        # Category: Paintings — mixed: some with suffix, one without
        self._make_image(art / "Paintings" / "sunset_2.png")
        self._make_image(art / "Paintings" / "ocean.jpg")
        self._make_image(art / "Paintings" / "hills_1.png")
        (art / "Paintings" / "thumbnails").mkdir()

        migrate_to_manifest(art_dir=art)

        data = read_manifest()
        assert len(data["categories"]) == 2

        # Alphabetical category order (no .order file)
        assert data["categories"][0]["name"] == "Paintings"
        assert data["categories"][1]["name"] == "Sketches"

        # Paintings: suffixed first sorted by N, then unsuffixed
        assert data["categories"][0]["images"] == ["hills_1.png", "sunset_2.png", "ocean.jpg"]

        # Sketches: sorted by _N suffix
        assert data["categories"][1]["images"] == ["dog_1.jpg", "cat_2.jpg", "bird_3.jpg"]

        # All previews default to null
        assert all(c["preview"] is None for c in data["categories"])

    def test_migration_respects_order_file(self, manifest_file, tmp_path):
        """Migration uses .order file for category ordering."""
        art = tmp_path / "art"

        self._make_image(art / "Alpha" / "a.jpg")
        (art / "Alpha" / "thumbnails").mkdir()
        self._make_image(art / "Beta" / "b.jpg")
        (art / "Beta" / "thumbnails").mkdir()
        self._make_image(art / "Gamma" / "g.jpg")
        (art / "Gamma" / "thumbnails").mkdir()

        # .order puts Gamma first, then Alpha (Beta unmentioned, sorts last)
        (art / ".order").write_text(json.dumps(["Gamma", "Alpha"]))

        migrate_to_manifest(art_dir=art)
        data = read_manifest()

        names = [c["name"] for c in data["categories"]]
        assert names == ["Gamma", "Alpha", "Beta"]

    def test_migration_no_art_dir_raises(self, manifest_file, tmp_path):
        """Migration raises FileNotFoundError if art directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            migrate_to_manifest(art_dir=tmp_path / "nonexistent")

    def test_migration_empty_art_dir(self, manifest_file, tmp_path):
        """Migration with an empty art directory produces empty categories list."""
        art = tmp_path / "art"
        art.mkdir()

        migrate_to_manifest(art_dir=art)
        data = read_manifest()
        assert data == {"categories": []}

    def test_migration_ignores_non_image_files(self, manifest_file, tmp_path):
        """Migration skips files that aren't image formats."""
        art = tmp_path / "art"
        cat = art / "Mixed"
        cat.mkdir(parents=True)
        (cat / "thumbnails").mkdir()

        self._make_image(cat / "real_1.jpg")
        (cat / "readme.txt").write_text("not an image")
        (cat / "data.json").write_text("{}")
        (cat / ".hidden").write_text("nope")

        migrate_to_manifest(art_dir=art)
        data = read_manifest()
        assert data["categories"][0]["images"] == ["real_1.jpg"]

    def test_migration_ignores_dot_directories(self, manifest_file, tmp_path):
        """Migration skips hidden directories (starting with .)."""
        art = tmp_path / "art"
        self._make_image(art / "Visible" / "a.jpg")
        (art / "Visible" / "thumbnails").mkdir()
        (art / ".hidden_cat").mkdir()
        self._make_image(art / ".hidden_cat" / "b.jpg")

        migrate_to_manifest(art_dir=art)
        data = read_manifest()
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "Visible"

    def test_migration_corrupt_order_file_falls_back(self, manifest_file, tmp_path):
        """If .order is invalid JSON, migration falls back to alphabetical."""
        art = tmp_path / "art"
        self._make_image(art / "Zulu" / "z.jpg")
        (art / "Zulu" / "thumbnails").mkdir()
        self._make_image(art / "Alpha" / "a.jpg")
        (art / "Alpha" / "thumbnails").mkdir()

        (art / ".order").write_text("{corrupt json!!")

        migrate_to_manifest(art_dir=art)
        data = read_manifest()
        names = [c["name"] for c in data["categories"]]
        assert names == ["Alpha", "Zulu"]
