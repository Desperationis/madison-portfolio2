from pathlib import Path
import logging
import urllib.parse

log = logging.getLogger("rich")

class DebugEasy:
    def __repr__(self):
        cls = self.__class__.__name__
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{cls}({attrs})"


class ArtPiece(DebugEasy):
    def __init__(self, path, thumbnail_path):
        self.path = path
        self.thumbnail_path = thumbnail_path

    def get_thumbnail_p(self):
        if self.thumbnail_path:
            return self.thumbnail_path

        return self.path

class Category(DebugEasy):
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".heif"}

    def __init__(self, name, cat_dir, images_list, preview_filename=None):
        self.name = name
        self.art_pieces = []
        self.thumbnail_p = None

        thumbnails_dir = cat_dir / "thumbnails"
        has_thumbnails = thumbnails_dir.is_dir()

        for filename in images_list:
            full_path = cat_dir / filename
            thumb_path = (thumbnails_dir / filename) if has_thumbnails and (thumbnails_dir / filename).is_file() else None
            self.art_pieces.append(ArtPiece(full_path, thumb_path))

        # Set category preview thumbnail
        if preview_filename:
            preview_path = cat_dir / preview_filename
            if has_thumbnails and (thumbnails_dir / preview_filename).is_file():
                self.thumbnail_p = thumbnails_dir / preview_filename
            else:
                self.thumbnail_p = preview_path
        elif self.art_pieces:
            self.thumbnail_p = self.art_pieces[0].get_thumbnail_p()

        # Full-size preview image (for OG meta tags)
        if preview_filename:
            self.preview_path = cat_dir / preview_filename
        elif self.art_pieces:
            self.preview_path = self.art_pieces[0].path
        else:
            self.preview_path = None


def dot_relative(parent: Path, child: Path) -> str | None:
    try:
        rel = child.relative_to(parent)
    except ValueError:
        log.warning(f"Skipping path outside project: {child}")
        return None
    if rel == Path("."):
        return "."
    return "./" + urllib.parse.quote(rel.as_posix(), safe='/')

def no_dot_relative(parent: Path, child: Path) -> str | None:
    result = dot_relative(parent, child)
    return result[1:] if result is not None else None
