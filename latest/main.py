from pathlib import Path
import sys
import logging
from rich.logging import RichHandler
from logging.handlers import RotatingFileHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import *
from http_gen import *

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

if not (cwd / "config.yaml").is_file():
    log.error("config.yaml not found in current directory. Run from the project root.")
    sys.exit(1)

detected_categories = []

SKIP_DIRS = {".git", ".github", "__pycache__", "latest", ".venv", "node_modules"}

for first_layer in sorted([p for p in cwd.iterdir() if p.is_dir()]):
    if first_layer.name.startswith(".") or first_layer.name in SKIP_DIRS:
        log.debug(f"Skipping non-art directory: {first_layer.name}")
        continue

    thumbnails_dir = first_layer / "thumbnails"
    second_layer = thumbnails_dir if thumbnails_dir.is_dir() else None

    log.info(f"Added {first_layer.name} as a category.")
    detected_categories.append(Category(first_layer.name, first_layer, second_layer))

# Remove invalid folders
detected_categories = [c for c in detected_categories if c.thumbnail_p]

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
