"""Filesystem operations for categories and images."""

from __future__ import annotations

import logging
import shutil
import urllib.parse
from pathlib import Path

logger = logging.getLogger(__name__)

from gui.thumbnail import delete_thumbnail, generate_thumbnail
from portfolio.manifest import read_manifest, write_manifest
from portfolio.utils import Category

ART_DIR = Path(__file__).resolve().parent.parent / "art"
IMAGE_EXTS = Category.IMAGE_EXTS


def validate_category_name(name: str) -> str:
    """Validate and clean a category name.

    Strips whitespace, then rejects empty strings, '.', '..', names containing
    '/', '\\', or null bytes, names starting with '.', and names longer than
    255 characters. Returns the cleaned name or raises ValueError.
    """
    name = name.strip()
    if not name:
        raise ValueError("Category name cannot be empty")
    if name in (".", ".."):
        raise ValueError(f"Category name cannot be '{name}'")
    if "/" in name or "\\" in name or "\0" in name:
        raise ValueError("Category name cannot contain '/', '\\', or null bytes")
    if name.startswith("."):
        raise ValueError("Category name cannot start with '.'")
    if len(name) > 255:
        raise ValueError("Category name cannot exceed 255 characters")
    return name


def create_category(name: str) -> dict:
    """Create a new category directory with a thumbnails subdirectory.

    Returns a category dict matching the list_categories format.
    Raises FileExistsError if the directory already exists.
    """
    name = validate_category_name(name)
    cat_dir = ART_DIR / name
    if cat_dir.exists():
        raise FileExistsError(f"Category '{name}' already exists")
    try:
        cat_dir.mkdir(parents=False)
        (cat_dir / "thumbnails").mkdir()
    except PermissionError as exc:
        logger.error("Permission denied creating category '%s' at %s", name, cat_dir)
        raise PermissionError(
            f"Permission denied while creating category '{name}' at {cat_dir}"
        ) from exc
    except OSError as exc:
        logger.error("OS error creating category '%s' at %s: %s", name, cat_dir, exc)
        raise OSError(
            f"OS error while creating category '{name}' at {cat_dir}: {exc}"
        ) from exc
    # Add to manifest
    manifest = read_manifest()
    manifest["categories"].append({"name": name, "preview": None, "images": []})
    write_manifest(manifest)

    logger.info("Created category '%s'", name)
    return {
        "name": name,
        "image_count": 0,
        "has_thumbnails": True,
        "thumbnail_url": None,
    }


def rename_category(old_name: str, new_name: str) -> dict:
    """Rename a category directory.

    Validates new_name, verifies old directory exists and new does not.
    Returns updated category dict matching list_categories format.
    """
    new_name = validate_category_name(new_name)
    old_dir = ART_DIR / old_name
    if not old_dir.exists():
        raise FileNotFoundError(f"Category '{old_name}' does not exist")
    new_dir = ART_DIR / new_name
    if new_dir.exists():
        raise FileExistsError(f"Category '{new_name}' already exists")
    try:
        old_dir.rename(new_dir)
    except PermissionError as exc:
        logger.error("Permission denied renaming category '%s' to '%s'", old_name, new_name)
        raise PermissionError(
            f"Permission denied while renaming category '{old_name}' to '{new_name}' at {old_dir}"
        ) from exc
    except OSError as exc:
        logger.error("OS error renaming category '%s' to '%s': %s", old_name, new_name, exc)
        raise OSError(
            f"OS error while renaming category '{old_name}' to '{new_name}' at {old_dir}: {exc}"
        ) from exc
    # Update manifest
    manifest = read_manifest()
    cat_images = []
    for cat in manifest["categories"]:
        if cat["name"] == old_name:
            cat["name"] = new_name
            cat_images = cat["images"]
            break
    write_manifest(manifest)

    logger.info("Renamed category '%s' to '%s'", old_name, new_name)

    # Build return dict
    thumbnails_dir = new_dir / "thumbnails"
    has_thumbnails = thumbnails_dir.is_dir()
    thumbnail_url = None
    if cat_images:
        first = cat_images[0]
        thumb_path = thumbnails_dir / first
        if has_thumbnails and thumb_path.is_file():
            thumbnail_url = f"/art/{new_name}/thumbnails/{first}"
        else:
            thumbnail_url = f"/art/{new_name}/{first}"
    return {
        "name": new_name,
        "image_count": len(cat_images),
        "has_thumbnails": has_thumbnails,
        "thumbnail_url": thumbnail_url,
    }


def delete_category(name: str, confirm: bool = False) -> None:
    """Delete a category directory and all its contents.

    Requires confirm=True as a safety measure. Raises ValueError if not
    confirmed, FileNotFoundError if the category does not exist.
    """
    if not confirm:
        raise ValueError("Deletion must be confirmed")
    cat_dir = ART_DIR / name
    if not cat_dir.exists():
        raise FileNotFoundError(f"Category '{name}' does not exist")
    try:
        shutil.rmtree(cat_dir)
    except PermissionError as exc:
        logger.error("Permission denied deleting category '%s' at %s", name, cat_dir)
        raise PermissionError(
            f"Permission denied while deleting category '{name}' at {cat_dir}"
        ) from exc
    except OSError as exc:
        logger.error("OS error deleting category '%s' at %s: %s", name, cat_dir, exc)
        raise OSError(
            f"OS error while deleting category '{name}' at {cat_dir}: {exc}"
        ) from exc
    # Remove from manifest
    manifest = read_manifest()
    manifest["categories"] = [c for c in manifest["categories"] if c["name"] != name]
    write_manifest(manifest)

    logger.info("Deleted category '%s'", name)


def list_categories() -> list[dict]:
    """Read categories from the manifest and return category metadata.

    Returns an ordered list of dicts with keys:
        name, image_count, has_thumbnails, thumbnail_url
    Order comes from the manifest's categories array.
    """
    manifest = read_manifest()
    categories = []
    for cat in manifest["categories"]:
        name = cat["name"]
        images = cat["images"]
        cat_dir = ART_DIR / name
        thumbnails_dir = cat_dir / "thumbnails"
        has_thumbnails = thumbnails_dir.is_dir()

        # Determine thumbnail URL from preview field or first image
        thumbnail_url = None
        preview = cat.get("preview")
        if preview:
            thumb_path = thumbnails_dir / preview
            if has_thumbnails and thumb_path.is_file():
                thumbnail_url = f"/art/{name}/thumbnails/{preview}"
            else:
                thumbnail_url = f"/art/{name}/{preview}"
        elif images:
            first = images[0]
            thumb_path = thumbnails_dir / first
            if has_thumbnails and thumb_path.is_file():
                thumbnail_url = f"/art/{name}/thumbnails/{first}"
            else:
                thumbnail_url = f"/art/{name}/{first}"

        categories.append({
            "name": name,
            "image_count": len(images),
            "has_thumbnails": has_thumbnails,
            "thumbnail_url": thumbnail_url,
        })

    return categories


def list_images(category_name: str) -> list[dict]:
    """List images in a category from the manifest with metadata from disk.

    Returns an ordered list of dicts with keys:
        filename, has_thumbnail, thumbnail_filename,
        full_url, thumbnail_url, size_bytes
    Order comes from the manifest's images array.
    """
    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    manifest = read_manifest()
    cat_entry = None
    for cat in manifest["categories"]:
        if cat["name"] == category_name:
            cat_entry = cat
            break
    if cat_entry is None:
        raise FileNotFoundError(f"Category '{category_name}' not found in manifest")

    thumbnails_dir = cat_dir / "thumbnails"

    # Build case-insensitive lookup of thumbnail filenames
    thumb_lookup: dict[str, str] = {}
    if thumbnails_dir.is_dir():
        for t in thumbnails_dir.iterdir():
            if t.is_file() and t.suffix.lower() in IMAGE_EXTS:
                thumb_lookup[t.name.lower()] = t.name

    encoded_cat = urllib.parse.quote(category_name, safe='')

    images = []
    for filename in cat_entry["images"]:
        f = cat_dir / filename
        if not f.is_file():
            continue  # Skip files listed in manifest but missing from disk

        thumb_name = thumb_lookup.get(filename.lower())
        has_thumbnail = thumb_name is not None

        encoded_filename = urllib.parse.quote(filename, safe='')
        full_url = f"/art/{encoded_cat}/{encoded_filename}"

        if has_thumbnail:
            encoded_thumb = urllib.parse.quote(thumb_name, safe='')
            thumbnail_url = f"/art/{encoded_cat}/thumbnails/{encoded_thumb}"
        else:
            thumbnail_url = full_url

        size_bytes = f.stat().st_size

        images.append({
            "filename": filename,
            "has_thumbnail": has_thumbnail,
            "thumbnail_filename": thumb_name,
            "full_url": full_url,
            "thumbnail_url": thumbnail_url,
            "size_bytes": size_bytes,
        })

    return images


def add_image(category_name: str, file_storage) -> dict:
    """Add an image to a category from a Flask FileStorage object.

    Validates extension, handles filename conflicts, saves the file,
    generates a thumbnail, and returns an image dict matching list_images format.
    """
    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    filename = file_storage.filename or ""
    if not filename:
        raise ValueError("No filename provided")

    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXTS:
        raise ValueError(f"Unsupported file extension: {ext}")

    # Handle filename conflicts by appending _1, _2, etc.
    stem = Path(filename).stem
    save_path = cat_dir / filename
    counter = 1
    while save_path.exists():
        new_name = f"{stem}_{counter}{ext}"
        save_path = cat_dir / new_name
        counter += 1
    final_filename = save_path.name

    # Save the file
    try:
        file_storage.save(save_path)
    except PermissionError as exc:
        logger.error("Permission denied saving image '%s' to category '%s'", final_filename, category_name)
        raise PermissionError(
            f"Permission denied while saving image '{final_filename}' to category '{category_name}' at {save_path}"
        ) from exc
    except OSError as exc:
        logger.error("OS error saving image '%s' to category '%s': %s", final_filename, category_name, exc)
        raise OSError(
            f"OS error while saving image '{final_filename}' to category '{category_name}' at {save_path}: {exc}"
        ) from exc
    logger.info("Added image '%s' to category '%s'", final_filename, category_name)

    # Generate thumbnail
    thumb_dir = cat_dir / "thumbnails"
    generate_thumbnail(save_path, thumb_dir)

    # Update manifest
    manifest = read_manifest()
    for cat in manifest["categories"]:
        if cat["name"] == category_name:
            cat["images"].append(final_filename)
            break
    write_manifest(manifest)

    # Build return dict
    encoded_cat = urllib.parse.quote(category_name, safe='')
    encoded_filename = urllib.parse.quote(final_filename, safe='')
    thumb_path = thumb_dir / final_filename

    return {
        "filename": final_filename,
        "has_thumbnail": thumb_path.exists(),
        "thumbnail_filename": final_filename if thumb_path.exists() else None,
        "full_url": f"/art/{encoded_cat}/{encoded_filename}",
        "thumbnail_url": f"/art/{encoded_cat}/thumbnails/{encoded_filename}" if thumb_path.exists() else f"/art/{encoded_cat}/{encoded_filename}",
        "size_bytes": save_path.stat().st_size,
    }


def delete_image(category_name: str, filename: str) -> None:
    """Delete an image and its thumbnail from a category.

    Raises FileNotFoundError if the image does not exist.
    """
    image_path = ART_DIR / category_name / filename
    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image '{filename}' does not exist in category '{category_name}'"
        )
    try:
        image_path.unlink()
    except PermissionError as exc:
        logger.error("Permission denied deleting image '%s' from category '%s'", filename, category_name)
        raise PermissionError(
            f"Permission denied while deleting image '{filename}' from category '{category_name}' at {image_path}"
        ) from exc
    except OSError as exc:
        logger.error("OS error deleting image '%s' from category '%s': %s", filename, category_name, exc)
        raise OSError(
            f"OS error while deleting image '{filename}' from category '{category_name}' at {image_path}: {exc}"
        ) from exc
    logger.info("Deleted image '%s' from category '%s'", filename, category_name)
    delete_thumbnail(ART_DIR / category_name, filename)

    # Update manifest
    manifest = read_manifest()
    for cat in manifest["categories"]:
        if cat["name"] == category_name:
            if filename in cat["images"]:
                cat["images"].remove(filename)
            # Clear preview if the deleted image was the preview
            if cat.get("preview") == filename:
                cat["preview"] = None
            break
    write_manifest(manifest)


def crop_thumbnail(category_name: str, filename: str, x: int, y: int, size: int) -> dict:
    """Crop the original image at the given region and save as the thumbnail.

    x, y, size are pixel coordinates on the original image defining a square
    crop region. The crop is resized to 800x800 and saved as the thumbnail.
    """
    from PIL import Image as _Image, ImageOps as _ImageOps

    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    image_path = cat_dir / filename
    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image '{filename}' does not exist in category '{category_name}'"
        )

    thumb_dir = cat_dir / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    img = _Image.open(image_path)
    img = _ImageOps.exif_transpose(img)

    if img.mode in ("RGBA", "P"):
        background = _Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[3])
        img = background

    # Clamp crop to image bounds
    w, h = img.size
    x = max(0, min(x, w - 1))
    y = max(0, min(y, h - 1))
    size = max(1, min(size, w - x, h - y))

    cropped = img.crop((x, y, x + size, y + size))
    cropped = cropped.resize((800, 800), _Image.LANCZOS)

    if cropped.mode != "RGB":
        cropped = cropped.convert("RGB")
    cropped.save(thumb_dir / filename, "JPEG", quality=85)

    logger.info("Cropped thumbnail for '%s' in category '%s' at (%d,%d) size %d", filename, category_name, x, y, size)

    encoded_cat = urllib.parse.quote(category_name, safe='')
    encoded_filename = urllib.parse.quote(filename, safe='')
    return {
        "filename": filename,
        "thumbnail_url": f"/art/{encoded_cat}/thumbnails/{encoded_filename}",
    }


def reset_thumbnail(category_name: str, filename: str) -> dict:
    """Regenerate the auto-thumbnail from the original image.

    Returns an updated image dict.
    """
    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    image_path = cat_dir / filename
    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image '{filename}' does not exist in category '{category_name}'"
        )

    thumb_dir = cat_dir / "thumbnails"
    generate_thumbnail(image_path, thumb_dir)
    logger.info("Reset thumbnail for '%s' in category '%s'", filename, category_name)

    encoded_cat = urllib.parse.quote(category_name, safe='')
    encoded_filename = urllib.parse.quote(filename, safe='')
    thumb_path = thumb_dir / filename
    return {
        "filename": filename,
        "thumbnail_url": f"/art/{encoded_cat}/thumbnails/{encoded_filename}" if thumb_path.exists() else f"/art/{encoded_cat}/{encoded_filename}",
    }


def set_category_preview(category_name: str, filename: str | None) -> dict:
    """Set the preview image for a category in the manifest.

    If filename is None, resets to default (first image).
    If filename is a string, validates it exists in the category's images list.
    Returns updated category metadata dict.
    """
    manifest = read_manifest()
    cat_entry = None
    for cat in manifest["categories"]:
        if cat["name"] == category_name:
            cat_entry = cat
            break
    if cat_entry is None:
        raise FileNotFoundError(f"Category '{category_name}' not found in manifest")

    if filename is not None and filename not in cat_entry["images"]:
        raise ValueError(f"Image '{filename}' is not in category '{category_name}'")

    cat_entry["preview"] = filename
    write_manifest(manifest)

    logger.info("Set preview for category '%s' to %s", category_name, filename)

    # Build return dict
    cat_dir = ART_DIR / category_name
    thumbnails_dir = cat_dir / "thumbnails"
    has_thumbnails = thumbnails_dir.is_dir()

    preview = filename or (cat_entry["images"][0] if cat_entry["images"] else None)
    thumbnail_url = None
    if preview:
        thumb_path = thumbnails_dir / preview
        encoded_cat = urllib.parse.quote(category_name, safe='')
        encoded_preview = urllib.parse.quote(preview, safe='')
        if has_thumbnails and thumb_path.is_file():
            thumbnail_url = f"/art/{encoded_cat}/thumbnails/{encoded_preview}"
        else:
            thumbnail_url = f"/art/{encoded_cat}/{encoded_preview}"

    return {
        "name": category_name,
        "preview": filename,
        "thumbnail_url": thumbnail_url,
    }


def move_image(source_category: str, filename: str, dest_category: str) -> dict:
    """Move an image (and its thumbnail) from one category to another.

    Updates the manifest for both categories. Returns the image dict in
    its new location (matching list_images format).
    Raises FileNotFoundError if source image or dest category doesn't exist.
    Raises FileExistsError if a file with the same name exists in dest.
    """
    if source_category == dest_category:
        raise ValueError("Source and destination categories are the same")

    src_dir = ART_DIR / source_category
    dst_dir = ART_DIR / dest_category
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Category '{source_category}' does not exist")
    if not dst_dir.is_dir():
        raise FileNotFoundError(f"Category '{dest_category}' does not exist")

    src_image = src_dir / filename
    if not src_image.is_file():
        raise FileNotFoundError(
            f"Image '{filename}' does not exist in category '{source_category}'"
        )

    dst_image = dst_dir / filename
    if dst_image.exists():
        raise FileExistsError(
            f"Image '{filename}' already exists in category '{dest_category}'"
        )

    # Move the image file
    shutil.move(str(src_image), str(dst_image))

    # Move thumbnail if it exists
    src_thumb = src_dir / "thumbnails" / filename
    dst_thumb_dir = dst_dir / "thumbnails"
    dst_thumb_dir.mkdir(exist_ok=True)
    if src_thumb.is_file():
        shutil.move(str(src_thumb), str(dst_thumb_dir / filename))

    # Update manifest: remove from source, add to dest
    manifest = read_manifest()
    for cat in manifest["categories"]:
        if cat["name"] == source_category:
            if filename in cat["images"]:
                cat["images"].remove(filename)
            if cat.get("preview") == filename:
                cat["preview"] = None
        elif cat["name"] == dest_category:
            cat["images"].append(filename)
    write_manifest(manifest)

    logger.info("Moved image '%s' from '%s' to '%s'", filename, source_category, dest_category)

    # Build return dict
    encoded_cat = urllib.parse.quote(dest_category, safe='')
    encoded_filename = urllib.parse.quote(filename, safe='')
    thumb_path = dst_thumb_dir / filename
    return {
        "filename": filename,
        "has_thumbnail": thumb_path.exists(),
        "thumbnail_filename": filename if thumb_path.exists() else None,
        "full_url": f"/art/{encoded_cat}/{encoded_filename}",
        "thumbnail_url": f"/art/{encoded_cat}/thumbnails/{encoded_filename}" if thumb_path.exists() else f"/art/{encoded_cat}/{encoded_filename}",
        "size_bytes": dst_image.stat().st_size,
    }


def reorder_images(category_name: str, ordered_filenames: list[str]) -> dict:
    """Reorder images in a category by updating the manifest array.

    Validates that ordered_filenames contains exactly the same filenames as
    the category's current images in the manifest. No files are renamed on
    disk — only the JSON array order changes.

    Returns an identity mapping dict {filename: filename} for API compat.
    Raises ValueError if ordered_filenames doesn't match existing images.
    Raises FileNotFoundError if the category doesn't exist.
    """
    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    manifest = read_manifest()
    cat_entry = None
    for cat in manifest["categories"]:
        if cat["name"] == category_name:
            cat_entry = cat
            break
    if cat_entry is None:
        raise FileNotFoundError(f"Category '{category_name}' not found in manifest")

    existing = set(cat_entry["images"])
    provided = set(ordered_filenames)

    if existing != provided:
        missing = existing - provided
        extra = provided - existing
        parts = []
        if missing:
            parts.append(f"missing: {sorted(missing)}")
        if extra:
            parts.append(f"extra: {sorted(extra)}")
        raise ValueError(f"Filename mismatch — {', '.join(parts)}")

    cat_entry["images"] = list(ordered_filenames)
    write_manifest(manifest)

    logger.info("Reordered %d images in category '%s'", len(ordered_filenames), category_name)

    return {f: f for f in ordered_filenames}


def reorder_categories(ordered_names: list[str]) -> list[str]:
    """Reorder categories by updating the manifest array order.

    Validates that ordered_names contains exactly the same category names
    as currently exist in the manifest. Returns the saved order.
    """
    manifest = read_manifest()
    cat_by_name = {cat["name"]: cat for cat in manifest["categories"]}
    existing = set(cat_by_name)
    provided = set(ordered_names)

    if existing != provided:
        missing = existing - provided
        extra = provided - existing
        parts = []
        if missing:
            parts.append(f"missing: {sorted(missing)}")
        if extra:
            parts.append(f"extra: {sorted(extra)}")
        raise ValueError(f"Category name mismatch — {', '.join(parts)}")

    manifest["categories"] = [cat_by_name[name] for name in ordered_names]
    write_manifest(manifest)

    logger.info("Reordered %d categories", len(ordered_names))
    return ordered_names
