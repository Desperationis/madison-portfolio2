# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python-based static site generator for an art portfolio (lunaportfolio.me). It reads a JSON manifest (`portfolio.json`) describing categories and image order, generates HTML gallery pages with lightbox viewers, and deploys via GitHub Pages.

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Generate the site (run from repo root)
python3 -m portfolio
```

Generated HTML files are written to `/latest/`. Deployment is automated via GitHub Actions — every push triggers `python3 main.py`, commits generated files, and pushes back.

## Architecture

**Manifest-driven pipeline**: `portfolio.json` (source of truth) → Category/ArtPiece models → HTML generation → static files

The `portfolio.json` manifest at the project root defines all portfolio content metadata: which categories exist, what order they appear in, which images each category contains (in order), and which image is the category preview. Images still live on disk under `art/`, but discovery and ordering are driven entirely by the manifest — no filesystem scanning or filename-encoded sort keys.

### Manifest schema

```json
{
  "categories": [
    {
      "name": "Category Name",
      "preview": "image.jpg",   // or null → use first image
      "images": ["image1.jpg", "image2.jpg"]
    }
  ]
}
```

- **Category order** = array order in `categories[]`
- **Image order** = array order in `images[]`
- **Category preview** = explicit `preview` field (`null` means first image)
- **Thumbnails** still live at `art/{category}/thumbnails/{filename}` on disk
- **`config.yaml`** stays separate for site settings (name, nav, footer)

### Key files

- `portfolio/manifest.py` — Read/write/validate `portfolio.json`. Provides `read_manifest()`, `write_manifest()`, `get_category()`, `save_category()`, `remove_category()`, and `migrate_to_manifest()` for bootstrapping from a legacy filesystem layout.
- `portfolio/utils.py` — Data models (`ArtPiece`, `Category`). `Category` accepts a name, directory path, and an ordered image list from the manifest. `ArtPiece` holds resolved paths for full-size and thumbnail images.
- `portfolio/__main__.py` — Entry point (`python -m portfolio`). Reads the manifest, constructs `Category` objects, generates index and category pages. Also supports `--migrate` to bootstrap `portfolio.json` from an existing `art/` directory.
- `portfolio/http_gen.py` — HTML generators (`IndexPage`, `CategoryPage`). Produces self-contained HTML with inline CSS/JS. CategoryPage includes a lightbox gallery with keyboard navigation.
- `config.yaml` — Site name, navigation links, footer text. Loaded by `http_gen.py`.

**Art directory convention**: Each directory inside `art/` is a category. Place full-size images in the category folder and smaller versions in a `thumbnails/` subfolder. Images are matched between layers by filename. Supported formats: JPG, JPEG, PNG, GIF, BMP, TIF, TIFF, WebP, HEIC, HEIF. Image ordering is manifest-driven — filenames do not encode sort order.

**Output structure**:
- `index.html` — Portfolio homepage with category grid (also a hardcoded fallback at repo root)
- `latest/{CategoryName}.html` — Per-category gallery pages

## GUI Portfolio Manager

A Flask-based local web app for visually managing the portfolio — edit categories, upload/reorder images, change site settings, and deploy to GitHub Pages, all from the browser.

### Running

```bash
python3 GUI.py
```

Starts a local server on `127.0.0.1:5555` (auto-selects next available port if busy) and opens the browser. Single-user, local-only — no auth needed.

### Architecture

The `gui/` package provides the backend; `GUI.py` is the entry point.

- `gui/config_ops.py` — Read/write `config.yaml` (site name, navigation, footer).
- `gui/file_ops.py` — CRUD operations for categories and images. Reads and writes `portfolio.json` via `portfolio/manifest.py` for all metadata (ordering, previews). File operations (save, delete, thumbnail generation) still happen on disk. Reordering is a manifest-only operation — no file renames.
- `gui/thumbnail.py` — Pillow-based auto-generation of thumbnails on image upload.
- `gui/git_ops.py` — Git status checks, deploy preflight validation, and the full deploy pipeline (generate site → git pull → commit → push) with step-by-step progress reporting.
- `gui/api.py` — Flask Blueprint with all `/api/*` REST endpoints for categories, images, navigation, settings, and deploy.
- `gui/templates/` — Jinja2 templates: `base.html` (shared layout), `index.html` (category grid), `category.html` (image grid with lightbox).
- `gui/static/editor.css` — Styles for overlay buttons, modals, toasts, drop zones.
- `gui/static/editor.js` — Frontend JS: API client, inline editing, modals, toasts, drag-and-drop (via SortableJS CDN).
- `gui/static/deploy.js` — Deploy button flow, preflight check, progress modal.

### Deploy Pipeline

The "Deploy to Website" button runs: preflight checks (clean working tree, remote reachable) → `python3 -m portfolio` to regenerate HTML → `git pull --rebase` → `git add/commit` → `git push`. Each step reports success/failure independently so errors are easy to diagnose.
