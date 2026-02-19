from pathlib import Path
import logging
import re

log = logging.getLogger("rich")

class DebugEasy:
    def __repr__(self):
        cls = self.__class__.__name__
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{cls}({attrs})"

    def __eq__(self, other):
            return type(self) is type(other) and vars(self) == vars(other)

    def __hash__(self):
        # order-independent; all your value types are hashable
        return hash(frozenset(vars(self).items()))


class ArtPiece(DebugEasy):
    def __init__(self, path, thumbnail_path):
        self.path = path
        self.thumbnail_path = thumbnail_path
        self.sort_key = self._extract_sort_key()

    def _extract_sort_key(self):
        """
        Extract numeric suffix from filename for sorting.
        Files ending with _INT (e.g., art_1.jpg, sketch_10.png) return that number.
        Files without the suffix return None.
        """
        stem = self.path.stem
        match = re.search(r'_(\d+)$', stem)
        if match:
            return int(match.group(1))
        return None
    
    def get_thumbnail_p(self):
        if self.thumbnail_path:
            return self.thumbnail_path

        return self.path

class Category(DebugEasy):
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".heif"}

    def __init__(self, name, first_layer_p, second_layer_p):
        self.name = name
        self.first_layer_p = first_layer_p
        self.second_layer_p = second_layer_p
        self.thumbnail_p = None
        self.art_pieces = []

        self._get_art()

        
    def _get_art(self):
        name_to_key_mapping = {}
        thumbnail_mapping = {}
        for p in self.first_layer_p.iterdir():
            if p.is_file() and p.suffix.lower() in self.IMAGE_EXTS:
                thumbnail_mapping[p] = None
                name_to_key_mapping[p.name] = p
                if self.thumbnail_p is None:
                    self.thumbnail_p = p

        if self.second_layer_p:
            for p in self.second_layer_p.iterdir():
                if p.is_file() and p.suffix.lower() in self.IMAGE_EXTS:
                    if p.name in name_to_key_mapping:
                        k = name_to_key_mapping[p.name]
                        thumbnail_mapping[k] = p
                        log.debug(f"Associated \"{self.name}/{p.name}\" art piece.")
                    else:
                        log.warning(f"WARNING: \"{self.name}/{p.name}\" thumbnail was not matched with anything.")

        for k in thumbnail_mapping:
            self.art_pieces.append(ArtPiece(k, thumbnail_mapping[k]))

        # Sort by sort_key: numbered files first (ascending), then files without suffix
        self.art_pieces.sort(key=lambda p: (p.sort_key is None, p.sort_key or 0))


def dot_relative(parent: Path, child: Path) -> str:
    rel = child.relative_to(parent)  # raises ValueError if not a descendant
    return "." if rel == Path(".") else f"./{rel.as_posix()}"

def no_dot_relative(parent: Path, child: Path) -> str:
    return dot_relative(parent, child)[1:]
