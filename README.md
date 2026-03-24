# Madison's Art Portfolio

Source for [lunaportfolio.me](https://lunaportfolio.me). The site rebuilds itself every time you push to GitHub.

## Quick Start

```bash
pip install -r requirements.txt
python3 GUI.py
```

This opens a local editor at `127.0.0.1:5555` where you can manage everything from the browser — add/remove categories, upload and reorder images, change site settings, and deploy to GitHub Pages with one click.

## How It Works

A JSON manifest (`portfolio.json`) defines all portfolio content: which categories exist, their order, which images each contains, and category previews. The static site generator reads this manifest, builds HTML gallery pages with a lightbox viewer, and writes them to `latest/`. GitHub Actions regenerates and deploys the site on every push.

## Managing Without the GUI

You can also edit `portfolio.json` and the `art/` directory by hand:

- **Add a category:** Create a folder in `art/`, add it to `portfolio.json`.
- **Add images:** Drop files into `art/{category}/` and list them in the manifest. Put thumbnails in `art/{category}/thumbnails/` with matching filenames.
- **Reorder:** Change the array order in `portfolio.json`.
- **Rebuild:** Run `python3 -m portfolio` to regenerate HTML.

## Don't Touch

`latest/`, `.github/`, `CLAUDE.md`, `.gitignore`, `CNAME` — these are managed automatically.
