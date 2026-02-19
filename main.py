from pathlib import Path
import logging
from rich.logging import RichHandler
from logging.handlers import RotatingFileHandler
from utils import *
from http_gen import *

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

file_handler = RotatingFileHandler(
    "gen.log",
    maxBytes=5_000_000,   # 5 MB
    backupCount=3,        # keep 3 old logs
    encoding="utf-8",
)
file_handler.setLevel(logging.NOTSET)
file_handler.setFormatter(logging.Formatter(FORMAT, datefmt="[%X]"))

logging.basicConfig(
    level=logging.NOTSET,
    handlers=[
        RichHandler(rich_tracebacks=True),  # console
        file_handler,                      # file
    ],
)

log = logging.getLogger("rich")




cwd = Path.cwd()
detected_categories = []

for first_layer in sorted([p for p in cwd.iterdir() if p.is_dir()]):
    second_layer = next((p for p in first_layer.iterdir() if p.is_dir()), None)

    log.info(f"Added {first_layer.name} as a category.")
    detected_categories.append(Category(first_layer.name, first_layer, second_layer))

# Remove invalid folders
detected_categories = [c for c in detected_categories if c.thumbnail_p]

generated_p = cwd / "latest"
generated_p.mkdir(parents=True, exist_ok=True)


index = IndexPage()
log.debug(detected_categories)
index.set_categories(detected_categories, cwd)
Path("index.html").write_text(index.get_content(), encoding="utf-8")

for c in detected_categories:
    page = CategoryPage(c, cwd)
    p = generated_p / f"{c.name}.html"
    p.write_text(page.get_content(), encoding="utf-8")
