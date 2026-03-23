"""Read/write/validate the portfolio.json manifest."""

import json
import os
import re
from pathlib import Path

MANIFEST_PATH = Path("portfolio.json")


class ManifestError(Exception):
    """Raised when the manifest is invalid."""


def validate_manifest(data: dict) -> None:
    """Check manifest structure. Raises ManifestError if malformed."""
    if not isinstance(data, dict):
        raise ManifestError("Manifest must be a JSON object")
    if "categories" not in data:
        raise ManifestError("Manifest must have a 'categories' key")
    if not isinstance(data["categories"], list):
        raise ManifestError("'categories' must be a list")
    for i, cat in enumerate(data["categories"]):
        if not isinstance(cat, dict):
            raise ManifestError(f"Category at index {i} must be an object")
        if "name" not in cat or not isinstance(cat["name"], str):
            raise ManifestError(f"Category at index {i} must have a 'name' string")
        if "images" not in cat or not isinstance(cat["images"], list):
            raise ManifestError(f"Category at index {i} must have an 'images' list")
        if not all(isinstance(img, str) for img in cat["images"]):
            raise ManifestError(f"Category at index {i}: all images must be strings")
        if "preview" not in cat:
            raise ManifestError(f"Category at index {i} must have a 'preview' field")
        if cat["preview"] is not None and not isinstance(cat["preview"], str):
            raise ManifestError(f"Category at index {i}: 'preview' must be a string or null")


def read_manifest() -> dict:
    """Read and validate portfolio.json. Raises FileNotFoundError if missing."""
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    validate_manifest(data)
    return data


def write_manifest(data: dict) -> None:
    """Validate and atomically write the manifest."""
    validate_manifest(data)
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(MANIFEST_PATH))


def get_category(name: str) -> dict | None:
    """Look up a category by name. Returns None if not found."""
    data = read_manifest()
    for cat in data["categories"]:
        if cat["name"] == name:
            return cat
    return None


def save_category(name: str, category_data: dict) -> None:
    """Update or insert a category entry by name."""
    data = read_manifest()
    for i, cat in enumerate(data["categories"]):
        if cat["name"] == name:
            data["categories"][i] = category_data
            write_manifest(data)
            return
    # Not found — append
    data["categories"].append(category_data)
    write_manifest(data)


def remove_category(name: str) -> None:
    """Remove a category entry by name."""
    data = read_manifest()
    data["categories"] = [c for c in data["categories"] if c["name"] != name]
    write_manifest(data)


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".heif"}


def _extract_sort_key(filename: str) -> tuple[bool, int]:
    """Extract numeric suffix for sorting. Returns (has_no_key, key) for sort stability."""
    stem = Path(filename).stem
    match = re.search(r'[\s_](\d+)$', stem)
    if match:
        return (False, int(match.group(1)))
    return (True, 0)


def migrate_to_manifest(art_dir: Path | None = None) -> dict:
    """Scan the filesystem and generate a portfolio.json manifest.

    Reads art/.order for category ordering (falls back to alphabetical).
    Sorts images within each category by existing _N suffix convention.
    Sets preview to null (first image default).
    """
    if art_dir is None:
        art_dir = Path("art")

    if not art_dir.is_dir():
        raise FileNotFoundError(f"Art directory not found: {art_dir}")

    # Discover category directories
    cat_dirs = sorted(
        [p for p in art_dir.iterdir() if p.is_dir() and not p.name.startswith(".")],
        key=lambda p: p.name,
    )

    # Read .order file for category ordering
    order_file = art_dir / ".order"
    ordered_names = None
    if order_file.is_file():
        try:
            saved_order = json.loads(order_file.read_text(encoding="utf-8"))
            if isinstance(saved_order, list):
                ordered_names = saved_order
                print(f"Read category order from {order_file}: {saved_order}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not read {order_file}: {e}")

    if ordered_names is not None:
        order_index = {name: i for i, name in enumerate(ordered_names)}
        cat_dirs.sort(key=lambda p: (order_index.get(p.name, len(ordered_names)), p.name))

    # Build manifest
    categories = []
    for cat_dir in cat_dirs:
        # Scan for image files (exclude thumbnails/ subdirectory)
        images = []
        for f in cat_dir.iterdir():
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                images.append(f.name)

        # Sort by _N suffix convention
        images.sort(key=_extract_sort_key)

        categories.append({
            "name": cat_dir.name,
            "preview": None,
            "images": images,
        })
        print(f"  {cat_dir.name}: {len(images)} images")

    data = {"categories": categories}
    write_manifest(data)
    print(f"\nWrote {MANIFEST_PATH} with {len(categories)} categories")
