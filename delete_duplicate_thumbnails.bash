#!/usr/bin/env bash
set -euo pipefail

# Delete files in "level 2" directories ONLY if their SHA256 matches any file
# in "level 1" directories.
#
# ROOT defaults to ".".
# Dry-run by default; pass --delete to actually remove files.

usage() {
  cat <<'EOF'
Usage:
  dedupe_level2_against_level1.sh [--root DIR] [--delete|--dry-run]

Options:
  --root DIR     Root directory to operate in (default: .)
  --delete, -D   Actually delete matching files (default: dry-run)
  --dry-run, -n  Print what would be deleted (default)
  --help, -h     Show this help
EOF
}

root="."
do_delete="false"

while (($#)); do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || { echo "ERROR: --root requires a value" >&2; exit 2; }
      root="$2"
      shift 2
      ;;
    --delete|-D) do_delete="true"; shift ;;
    --dry-run|-n) do_delete="false"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "ERROR: Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -d "$root" ]] || { echo "ERROR: root is not a directory: $root" >&2; exit 2; }

hash_file() {
  # Prints the sha256 hash for $1, or returns non-zero on failure.
  local f="$1" line
  line="$(sha256sum -- "$f" 2>/dev/null)" || return 1
  printf '%s\n' "${line%% *}"
}

declare -A l1_hashes=()

# Level-1 files: root/*/<file>  (mindepth 2, maxdepth 2)
while IFS= read -r -d '' f; do
  if h="$(hash_file "$f")"; then
    l1_hashes["$h"]=1
  else
    echo "WARN: could not hash (skipping): $f" >&2
  fi
done < <(find "$root" -mindepth 2 -maxdepth 2 -type f -print0 2>/dev/null || true)

deleted=0
scanned=0

# Level-2 files: root/*/*/<file> (mindepth 3, maxdepth 3)
while IFS= read -r -d '' f; do
  ((++scanned))
  if h="$(hash_file "$f")"; then
    if [[ -n "${l1_hashes[$h]:-}" ]]; then
      if [[ "$do_delete" == "true" ]]; then
        rm -- "$f"
        echo "DELETED: $f"
      else
        echo "DRY-RUN (would delete): $f"
      fi
      ((++deleted))
    fi
  else
    echo "WARN: could not hash (skipping): $f" >&2
  fi
done < <(find "$root" -mindepth 3 -maxdepth 3 -type f -print0 2>/dev/null || true)

echo "Done. Scanned level-2 files: $scanned. Matched: $deleted. Mode: $([[ "$do_delete" == "true" ]] && echo delete || echo dry-run)"
