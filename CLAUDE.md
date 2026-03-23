# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python-based static site generator for an art portfolio (lunaportfolio.me). It scans image directories, generates HTML gallery pages with lightbox viewers, and deploys via GitHub Pages.

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Generate the site (run from repo root)
python3 -m portfolio
```

Generated HTML files are written to `/latest/`. Deployment is automated via GitHub Actions — every push triggers `python3 main.py`, commits generated files, and pushes back.

## Architecture

**Generation pipeline**: Directory scan → Category/ArtPiece models → HTML generation → static files

Key files:
- `portfolio/utils.py` — Data models (`ArtPiece`, `Category`). Category scans a directory for images and an optional `thumbnails/` subfolder. Art pieces sort by numeric filename suffix (e.g. `art_3.jpg` sorts as 3).
- `portfolio/__main__.py` — Entry point (`python -m portfolio`). Discovers directories inside `art/` as categories, filters to those with thumbnails, generates index and category pages.
- `portfolio/http_gen.py` — HTML generators (`IndexPage`, `CategoryPage`). Produces self-contained HTML with inline CSS/JS. CategoryPage includes a lightbox gallery with keyboard navigation.
- `config.yaml` — Site name, navigation links, footer text. Loaded by `http_gen.py`.

**Art directory convention**: Each directory inside `art/` is a category. Place full-size images in the category folder and smaller versions in a `thumbnails/` subfolder. Images are matched between layers by filename. Supported formats: JPG, JPEG, PNG, GIF, BMP, TIF, TIFF, WebP, HEIC, HEIF.

**Output structure**:
- `index.html` — Portfolio homepage with category grid (also a hardcoded fallback at repo root)
- `latest/{CategoryName}.html` — Per-category gallery pages
