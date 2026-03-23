from pathlib import Path
import sys
import logging
from rich.logging import RichHandler
from logging.handlers import RotatingFileHandler

from .utils import *
from .http_gen import *
from .manifest import migrate_to_manifest, read_manifest, MANIFEST_PATH

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

try:
    log_path = Path(__file__).resolve().parent.parent / "gen.log"
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5_000_000,   # 5 MB
        backupCount=3,        # keep 3 old logs
        encoding="utf-8",
    )
    file_handler.setLevel(logging.NOTSET)
    file_handler.setFormatter(logging.Formatter(FORMAT, datefmt="[%X]"))
    handlers = [RichHandler(rich_tracebacks=True), file_handler]
except OSError:
    handlers = [RichHandler(rich_tracebacks=True)]

logging.basicConfig(
    level=logging.NOTSET,
    handlers=handlers,
)

log = logging.getLogger("rich")




cwd = Path.cwd()

if "--migrate" in sys.argv:
    art_dir = cwd / "art"
    if not art_dir.is_dir():
        log.error("art/ directory not found. Place art category folders inside art/.")
        sys.exit(1)
    migrate_to_manifest(art_dir)
    sys.exit(0)

if not (cwd / "config.yaml").is_file():
    log.error("config.yaml not found in current directory. Run from the project root.")
    sys.exit(1)

if not MANIFEST_PATH.is_file():
    log.error("portfolio.json not found. Run 'python -m portfolio --migrate' to create it from your art/ directory.")
    sys.exit(1)

art_dir = cwd / "art"
manifest = read_manifest()

detected_categories = []
for cat_entry in manifest["categories"]:
    cat_dir = art_dir / cat_entry["name"]
    if not cat_dir.is_dir():
        log.warning(f"Skipping category '{cat_entry['name']}': directory not found at {cat_dir}")
        continue

    cat = Category(cat_entry["name"], cat_dir, cat_entry["images"], cat_entry.get("preview"))
    if cat.thumbnail_p:
        log.info(f"Added {cat_entry['name']} as a category.")
        detected_categories.append(cat)

generated_p = cwd / "latest"
generated_p.mkdir(parents=True, exist_ok=True)


config = load_config()

index = IndexPage(config)
log.debug(detected_categories)
index.set_categories(detected_categories, cwd)
try:
    Path("index.html").write_text(index.get_content(), encoding="utf-8")
except OSError as e:
    log.error(f"Failed to write index.html: {e}")

for c in detected_categories:
    page = CategoryPage(c, cwd, config)
    p = generated_p / f"{c.name}.html"
    try:
        p.write_text(page.get_content(), encoding="utf-8")
    except OSError as e:
        log.error(f"Failed to write {p}: {e}")
