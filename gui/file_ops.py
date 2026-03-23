"""Filesystem operations for categories and images."""

import logging
import re
import shutil
import threading
import urllib.parse
from pathlib import Path

logger = logging.getLogger(__name__)

from gui.thumbnail import delete_thumbnail, generate_thumbnail
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
    logger.info("Renamed category '%s' to '%s'", old_name, new_name)

    # Build return dict
    images = [
        f for f in new_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS
    ]
    thumbnail_url = None
    if images:
        first = sorted(images, key=lambda p: p.name)[0]
        thumbnail_url = f"/art/{new_name}/{first.name}"
    return {
        "name": new_name,
        "image_count": len(images),
        "has_thumbnails": (new_dir / "thumbnails").is_dir(),
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
    logger.info("Deleted category '%s'", name)


def list_categories() -> list[dict]:
    """Scan ART_DIR for subdirectories and return category metadata.

    Returns a sorted list of dicts with keys:
        name, image_count, has_thumbnails, thumbnail_url
    """
    categories = []
    try:
        entries = list(ART_DIR.iterdir())
    except PermissionError as exc:
        raise PermissionError(
            f"Permission denied while listing categories at {ART_DIR}"
        ) from exc
    except OSError as exc:
        raise OSError(
            f"OS error while listing categories at {ART_DIR}: {exc}"
        ) from exc
    for entry in entries:
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        # Count image files (top-level only, not thumbnails/)
        try:
            images = [
                f for f in entry.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS
            ]
        except PermissionError as exc:
            raise PermissionError(
                f"Permission denied while reading category '{entry.name}' at {entry}"
            ) from exc
        except OSError as exc:
            raise OSError(
                f"OS error while reading category '{entry.name}' at {entry}: {exc}"
            ) from exc
        image_count = len(images)

        thumbnails_dir = entry / "thumbnails"
        has_thumbnails = thumbnails_dir.is_dir()

        # First image as thumbnail URL (sorted for determinism)
        thumbnail_url = None
        if images:
            first = sorted(images, key=lambda p: p.name)[0]
            thumbnail_url = f"/art/{entry.name}/{first.name}"

        categories.append({
            "name": entry.name,
            "image_count": image_count,
            "has_thumbnails": has_thumbnails,
            "thumbnail_url": thumbnail_url,
        })

    categories.sort(key=lambda c: c["name"])
    return categories


def _extract_sort_key(stem: str) -> int | None:
    """Extract numeric suffix from filename stem for sorting.

    Mirrors ArtPiece._extract_sort_key() logic.
    """
    match = re.search(r'[\s_](\d+)$', stem)
    if match:
        return int(match.group(1))
    return None


def list_images(category_name: str) -> list[dict]:
    """List images in a category with metadata.

    Returns a sorted list of dicts with keys:
        filename, sort_key, has_thumbnail, thumbnail_filename,
        full_url, thumbnail_url, size_bytes
    """
    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    thumbnails_dir = cat_dir / "thumbnails"

    # Build case-insensitive lookup of thumbnail filenames
    thumb_lookup: dict[str, str] = {}
    if thumbnails_dir.is_dir():
        try:
            for t in thumbnails_dir.iterdir():
                if t.is_file() and t.suffix.lower() in IMAGE_EXTS:
                    thumb_lookup[t.name.lower()] = t.name
        except PermissionError as exc:
            raise PermissionError(
                f"Permission denied while reading thumbnails for category '{category_name}' at {thumbnails_dir}"
            ) from exc
        except OSError as exc:
            raise OSError(
                f"OS error while reading thumbnails for category '{category_name}' at {thumbnails_dir}: {exc}"
            ) from exc

    encoded_cat = urllib.parse.quote(category_name, safe='')

    images = []
    try:
        dir_contents = list(cat_dir.iterdir())
    except PermissionError as exc:
        raise PermissionError(
            f"Permission denied while listing images in category '{category_name}' at {cat_dir}"
        ) from exc
    except OSError as exc:
        raise OSError(
            f"OS error while listing images in category '{category_name}' at {cat_dir}: {exc}"
        ) from exc
    for f in dir_contents:
        if not f.is_file() or f.suffix.lower() not in IMAGE_EXTS:
            continue

        sort_key = _extract_sort_key(f.stem)
        thumb_name = thumb_lookup.get(f.name.lower())
        has_thumbnail = thumb_name is not None

        encoded_filename = urllib.parse.quote(f.name, safe='')
        full_url = f"/art/{encoded_cat}/{encoded_filename}"

        if has_thumbnail:
            encoded_thumb = urllib.parse.quote(thumb_name, safe='')
            thumbnail_url = f"/art/{encoded_cat}/thumbnails/{encoded_thumb}"
        else:
            thumbnail_url = full_url

        try:
            size_bytes = f.stat().st_size
        except PermissionError as exc:
            raise PermissionError(
                f"Permission denied while reading image '{f.name}' in category '{category_name}'"
            ) from exc
        except OSError as exc:
            raise OSError(
                f"OS error while reading image '{f.name}' in category '{category_name}': {exc}"
            ) from exc

        images.append({
            "filename": f.name,
            "sort_key": sort_key,
            "has_thumbnail": has_thumbnail,
            "thumbnail_filename": thumb_name,
            "full_url": full_url,
            "thumbnail_url": thumbnail_url,
            "size_bytes": size_bytes,
        })

    images.sort(key=lambda img: (img["sort_key"] is None, img["sort_key"] or 0))
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

    # Build return dict
    encoded_cat = urllib.parse.quote(category_name, safe='')
    encoded_filename = urllib.parse.quote(final_filename, safe='')
    sort_key = _extract_sort_key(save_path.stem)
    thumb_path = thumb_dir / final_filename

    return {
        "filename": final_filename,
        "sort_key": sort_key,
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


_reorder_lock = threading.Lock()


def reorder_images(category_name: str, ordered_filenames: list[str]) -> dict:
    """Reorder images in a category using a two-phase atomic rename.

    Validates that ordered_filenames contains exactly the same filenames as
    currently exist in the category. Computes new filenames with sequential
    numeric suffixes, renames via temporary names to avoid collisions, and
    renames corresponding thumbnails in sync.

    Returns a mapping dict: {old_filename: new_filename}.
    Raises ValueError if ordered_filenames doesn't match existing files.
    Raises FileNotFoundError if the category doesn't exist.
    """
    cat_dir = ART_DIR / category_name
    if not cat_dir.is_dir():
        raise FileNotFoundError(f"Category '{category_name}' does not exist")

    # Get current image filenames
    existing = {
        f.name for f in cat_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS
    }
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

    # Compute new filenames: strip existing numeric suffix, append _{position}
    suffix_re = re.compile(r'[\s_]\d+$')
    rename_map = {}
    for i, old_name in enumerate(ordered_filenames, start=1):
        old_path = Path(old_name)
        stem = old_path.stem
        ext = old_path.suffix
        clean_stem = suffix_re.sub('', stem)
        new_name = f"{clean_stem}_{i}{ext}"
        rename_map[old_name] = new_name

    thumb_dir = cat_dir / "thumbnails"
    has_thumbs = thumb_dir.is_dir()

    # Build case-insensitive thumbnail lookup
    thumb_lookup: dict[str, str] = {}
    if has_thumbs:
        for t in thumb_dir.iterdir():
            if t.is_file():
                thumb_lookup[t.name.lower()] = t.name

    try:
        with _reorder_lock:
            # Phase 1: rename all files to temporary names
            temp_names = {}
            for i, old_name in enumerate(ordered_filenames):
                ext = Path(old_name).suffix
                tmp_name = f"__reorder_tmp_{i}{ext}"
                (cat_dir / old_name).rename(cat_dir / tmp_name)
                temp_names[i] = tmp_name

                # Also rename thumbnail if it exists
                actual_thumb = thumb_lookup.get(old_name.lower())
                if has_thumbs and actual_thumb:
                    thumb_ext = Path(actual_thumb).suffix
                    thumb_tmp = f"__reorder_tmp_{i}{thumb_ext}"
                    (thumb_dir / actual_thumb).rename(thumb_dir / thumb_tmp)

            # Phase 2: rename temp files to final new names
            for i, old_name in enumerate(ordered_filenames):
                new_name = rename_map[old_name]
                ext = Path(old_name).suffix
                tmp_name = f"__reorder_tmp_{i}{ext}"
                (cat_dir / tmp_name).rename(cat_dir / new_name)

                # Also rename thumbnail
                actual_thumb = thumb_lookup.get(old_name.lower())
                if has_thumbs and actual_thumb:
                    thumb_ext = Path(actual_thumb).suffix
                    thumb_tmp = f"__reorder_tmp_{i}{thumb_ext}"
                    new_thumb = f"{Path(new_name).stem}{thumb_ext}"
                    (thumb_dir / thumb_tmp).rename(thumb_dir / new_thumb)
    except PermissionError as exc:
        logger.error("Permission denied reordering images in category '%s'", category_name)
        raise PermissionError(
            f"Permission denied while reordering images in category '{category_name}' at {cat_dir}"
        ) from exc
    except OSError as exc:
        logger.error("OS error reordering images in category '%s': %s", category_name, exc)
        raise OSError(
            f"OS error while reordering images in category '{category_name}' at {cat_dir}: {exc}"
        ) from exc
    logger.info("Reordered %d images in category '%s'", len(rename_map), category_name)

    return rename_map
