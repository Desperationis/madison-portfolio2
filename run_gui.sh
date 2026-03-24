#!/bin/bash
# Smart launcher for the Portfolio GUI.
# Handles startup sync, error recovery, and the nuclear reset option.
# Called by the macOS .app bundle — can also be run directly.

REPO_DIR="$HOME/Desktop/madison-portfolio2"
cd "$REPO_DIR" || {
  osascript -e 'display dialog "Could not find the portfolio folder on your Desktop." buttons {"OK"} default button "OK" with icon stop with title "Madison Portfolio"'
  exit 1
}

# --- Helper: nuclear reset (pure bash, no Python needed) ---
do_nuclear_reset() {
  echo ""
  echo "=== Resetting everything to match the website... ==="
  echo ""

  # Remove stale lock file
  rm -f .git/index.lock 2>/dev/null

  # Abort any in-progress operations
  git merge --abort 2>/dev/null
  git rebase --abort 2>/dev/null
  git cherry-pick --abort 2>/dev/null

  # Make sure we're on a real branch
  git checkout main 2>/dev/null || git checkout master 2>/dev/null

  # Fetch and hard reset
  git fetch origin || {
    osascript -e 'display dialog "Could not connect to the internet. Check your Wi-Fi and try again." buttons {"OK"} default button "OK" with icon stop with title "Madison Portfolio"'
    return 1
  }

  BRANCH=$(git rev-parse --abbrev-ref HEAD)
  git reset --hard "origin/$BRANCH"
  git clean -fd

  echo ""
  echo "Done! Everything matches the live website."
  echo ""
  return 0
}

# --- Startup: check for remote changes ---
echo "Checking for updates..."

# Quick fetch to see if there are remote changes
if git fetch origin 2>/dev/null; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
  LOCAL=$(git rev-parse HEAD 2>/dev/null)
  REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null)
  DIRTY=$(git status --porcelain 2>/dev/null)

  if [ "$LOCAL" != "$REMOTE" ] || [ -n "$DIRTY" ]; then
    # There are differences — ask the user what to do
    if [ -n "$DIRTY" ]; then
      CHOICE=$(osascript -e '
        set LF to ASCII character 10
        set theMsg to "Your portfolio has unsaved local changes that don'\''t match the website." & LF & LF & "Pull: Download updates (keeps your local changes)" & LF & "Nuke Everything: Wipe local changes and match the website exactly" & LF & "Cancel: Don'\''t start the editor"
        display dialog theMsg buttons {"Cancel", "Nuke Everything", "Pull"} default button "Pull" with icon note with title "Madison Portfolio"
        button returned of result
      ' 2>/dev/null)
    else
      CHOICE=$(osascript -e '
        set LF to ASCII character 10
        set theMsg to "The website has been updated since you last opened the editor." & LF & LF & "Pull: Download the latest changes" & LF & "Nuke Everything: Reset and match the website exactly" & LF & "Cancel: Don'\''t start the editor"
        display dialog theMsg buttons {"Cancel", "Nuke Everything", "Pull"} default button "Pull" with icon note with title "Madison Portfolio"
        button returned of result
      ' 2>/dev/null)
    fi

    case "$CHOICE" in
      "Pull")
        echo "Pulling latest changes..."
        git pull --rebase origin "$BRANCH" 2>&1 || {
          # Pull failed (merge conflict etc) — offer nuclear reset
          CHOICE2=$(osascript -e '
            set LF to ASCII character 10
            set theMsg to "The pull failed - there might be a conflict." & LF & LF & "Would you like to reset everything to match the website?"
            display dialog theMsg buttons {"Cancel", "Reset Everything"} default button "Reset Everything" with icon stop with title "Madison Portfolio"
            button returned of result
          ' 2>/dev/null)
          if [ "$CHOICE2" = "Reset Everything" ]; then
            do_nuclear_reset || exit 1
          else
            exit 0
          fi
        }
        ;;
      "Nuke Everything")
        do_nuclear_reset || exit 1
        ;;
      *)
        # Cancel or closed the dialog
        echo "Cancelled."
        exit 0
        ;;
    esac
  else
    echo "Already up to date."
  fi
else
  echo "Could not check for updates (no internet?). Starting with local version..."
fi

# --- Launch the GUI ---
# Skip the built-in sync in GUI.py since we already handled it above
export PORTFOLIO_SKIP_SYNC=1

echo ""
echo "Starting Portfolio Manager..."
echo ""

while true; do
  python3 GUI.py
  EXIT_CODE=$?

  if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ]; then
    # Normal exit (code 0) or Ctrl+C (code 130)
    break
  fi

  # GUI crashed or failed to start — offer recovery
  echo ""
  echo "The Portfolio Manager exited with an error (code $EXIT_CODE)."
  echo ""

  CHOICE=$(osascript -e '
    set LF to ASCII character 10
    set theMsg to "Something went wrong starting the Portfolio Manager." & LF & LF & "Would you like to reset everything and try again?"
    display dialog theMsg buttons {"Quit", "Reset and Retry"} default button "Reset and Retry" with icon stop with title "Madison Portfolio"
    button returned of result
  ' 2>/dev/null)

  if [ "$CHOICE" = "Reset and Retry" ]; then
    do_nuclear_reset || break
    echo "Retrying..."
    echo ""
  else
    break
  fi
done

echo ""
echo "Portfolio Manager closed."
