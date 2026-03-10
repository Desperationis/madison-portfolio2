# Bug Fix Checklist

## .github/workflows/pythonrebuild.yaml

- [x] **[Critical] Fix CI pipeline file paths (lines 32-37)** — Change `requirements.txt` to `latest/requirements.txt` and `python3 main.py` to `PYTHONPATH=. python3 latest/main.py`. Done when: CI workflow runs successfully on push.

## latest/main.py

- [x] **[Critical] Fix import path for utils.py (line 5)** — Add `sys.path.insert(0, str(Path(__file__).parent.parent))` before imports so `python3 latest/main.py` works without PYTHONPATH workaround.
- [x] **[High] Filter out non-art directories from category scanning (lines 35-39)** — Skip `.git`, `.github`, `__pycache__`, `latest`, and dot-prefixed directories. Done when: log shows only art directories.
- [x] **[High] Look specifically for `thumbnails/` subdirectory instead of first arbitrary subdirectory (line 36)** — Replace `next((p for p in first_layer.iterdir() if p.is_dir()), None)` with explicit `thumbnails/` check.
- [x] **[Medium] Add error handling around file write operations (lines 51, 56)** — Wrap `write_text()` in try/except so one failing page doesn't crash the build.
- [x] **[Medium] Fix RotatingFileHandler to use absolute path with error handling (lines 10-15)** — Use `Path(__file__).parent.parent / "gen.log"` and wrap in try/except.
- [x] **[Low] Add validation that cwd is the project root (line 32)** — Check for `config.yaml` existence before proceeding.

## utils.py

- [x] **[High] URL-encode file paths in `dot_relative()` and `no_dot_relative()` (lines 85-91)** — Apply `urllib.parse.quote(path, safe='/')` so spaces become `%20` and `+` becomes `%2B`.
- [x] **[Medium] Fix DebugEasy.__hash__ for objects with unhashable attributes (lines 16-18)** — Set `__hash__ = None` on Category since it contains mutable list.
- [x] **[Medium] Broaden sort key regex to match space-separated numbers (lines 27-37)** — Change regex from `r'_(\d+)$'` to `r'[\s_](\d+)$'` so "Wingspan Inks 6" gets sort_key=6.
- [x] **[Low] Fix fragile `sort_key or 0` pattern (line 82)** — Replace with `p.sort_key if p.sort_key is not None else 0`.
- [x] **[Low] Add case-insensitive thumbnail matching (line 71)** — Use `.lower()` when building and querying the name mapping.
- [x] **[Low] Add error handling around `iterdir()` calls (lines 61, 69)** — Wrap in try/except for PermissionError/OSError.
- [x] **[Low] Handle symlinks pointing outside the project (line 86)** — Catch `ValueError` from `relative_to()` and skip with a warning.

## latest/http_gen.py

- [x] **[Medium] HTML-escape all user-derived strings in templates (lines 27, 150, 154, 189, 260, 271, 315)** — Use `html.escape()` for category names, config values, and filenames.
- [x] **[Medium] Replace hardcoded "Ballet dancers" alt text with actual image description (line 315)** — Use filename stem with HTML escaping as alt text.
- [x] **[Medium] Add alt attribute to index page category thumbnails (line 152)** — Add `alt="{html.escape(c.name)}"` to img elements.
- [x] **[Medium] Add error handling and validation to load_config() (lines 6-10)** — Validate file existence, YAML parsing, and required keys with clear error messages.
- [x] **[Low] Cache config.yaml loading (lines 14-15, 170-171)** — Load config once and pass to page constructors instead of re-reading per page.
