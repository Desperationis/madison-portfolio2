"""Pillow-based thumbnail generation, regeneration, and deletion."""

import logging
import shutil
from pathlib import Path

from PIL import Image, ImageOps

from portfolio.utils import Category

IMAGE_EXTS = Category.IMAGE_EXTS

THUMBNAIL_MAX_SIZE = 800

log = logging.getLogger(__name__)


def generate_thumbnail(
    image_path: Path,
    thumbnail_dir: Path,
    max_size: int = THUMBNAIL_MAX_SIZE,
) -> Path:
    """Generate a thumbnail for the given image.

    Opens the image, auto-rotates based on EXIF, handles transparency,
    center-crops to max_size x max_size, and saves as JPEG.
    Falls back to copying the original if Pillow can't process it.
    """
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    output_path = thumbnail_dir / image_path.name

    try:
        img = Image.open(image_path)

        # 3.1.3: Auto-rotate based on EXIF orientation
        img = ImageOps.exif_transpose(img)

        # 3.1.4: Handle transparency — composite onto white background
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            # Convert P mode to RGBA first for proper compositing
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[3])
            img = background

        # 3.1.5: Center-crop and resize
        img = ImageOps.fit(img, (max_size, max_size), method=Image.LANCZOS)

        # 3.1.6: Save as JPEG
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=85)

    except Exception as e:
        # 3.1.7: Fallback — copy original if Pillow can't handle it
        log.warning(
            "Could not generate thumbnail for %s: %s. Copying original as fallback.",
            image_path,
            e,
        )
        shutil.copy2(image_path, output_path)

    return output_path


def delete_thumbnail(category_path: Path, filename: str) -> bool:
    """Delete a single thumbnail file from a category's thumbnails directory.

    Returns True if the file was deleted, False if it didn't exist.
    """
    thumb_path = category_path / "thumbnails" / filename
    if thumb_path.exists():
        thumb_path.unlink()
        return True
    return False
